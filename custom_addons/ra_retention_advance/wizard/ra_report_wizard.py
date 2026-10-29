import base64
import io
from collections import defaultdict

import xlsxwriter

from odoo import _, fields, models


class RaReportWizard(models.TransientModel):
    _name = 'ra.report.wizard'
    _description = 'Retention and Advance Report'

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    date = fields.Date(string='As at', required=True, default=fields.Date.context_today)
    partner_ids = fields.Many2many(
        'res.partner', string='Customers', help="Leave empty for all customers.")
    line_ids = fields.One2many('ra.report.line', 'wizard_id', string='Lines')

    # ------------------------------------------------------------------
    def _get_report_values(self):
        self.ensure_one()
        Move = self.env['account.move']
        base = [
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'posted'),
            ('date', '<=', self.date),
        ]
        partners = self.partner_ids.commercial_partner_id
        if partners:
            base.append(('commercial_partner_id', 'in', partners.ids))
        data = defaultdict(lambda: defaultdict(float))

        # Total invoiced: work done (without VAT), credit notes counted negative.
        for partner, order, total in Move._read_group(
                base + [('move_type', 'in', ('out_invoice', 'out_refund'))],
                ['commercial_partner_id', 'ra_sale_order_id'],
                ['amount_untaxed_signed:sum']):
            data[(partner.id, order.id)]['invoiced'] += total

        # Retention and advance movements (company currency).
        for partner, order, ra_type, amount in Move._read_group(
                base + [('ra_type', '!=', False)],
                ['commercial_partner_id', 'ra_sale_order_id', 'ra_type'],
                ['ra_amount:sum']):
            data[(partner.id, order.id)][ra_type] += amount

        # Advance received.
        payments = self.env['account.payment'].search([
            ('company_id', '=', self.company_id.id),
            ('payment_type', '=', 'inbound'),
            ('partner_type', '=', 'customer'),
            ('state', 'in', ('in_process', 'paid')),
            ('ra_is_advance', '=', True),
            ('date', '<=', self.date),
        ])
        for payment in payments:
            partner = payment.partner_id.commercial_partner_id
            if partners and partner not in partners:
                continue
            data[(partner.id, payment.ra_sale_order_id.id)]['received'] += abs(
                payment.amount_company_currency_signed)

        values = []
        for (partner_id, order_id), d in sorted(data.items()):
            held = d['transfer'] - d['return']
            released = d['release']
            recovered = d['advance_apply'] - d['advance_return']
            values.append({
                'partner_id': partner_id,
                'sale_order_id': order_id or False,
                'total_invoiced': d['invoiced'],
                'retention_held': held,
                'retention_released': released,
                'retention_balance': held - released,
                'advance_received': d['received'],
                'advance_recovered': recovered,
                'advance_balance': d['received'] - recovered,
            })
        return values

    def action_compute(self):
        self.ensure_one()
        self.line_ids.unlink()
        self.env['ra.report.line'].create(
            [dict(vals, wizard_id=self.id) for vals in self._get_report_values()])
        return True

    def action_export_xlsx(self):
        self.ensure_one()
        self.action_compute()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(_("Retention and Advance"))
        title = workbook.add_format({'bold': True, 'font_size': 14})
        head = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1, 'text_wrap': True})
        money = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        text = workbook.add_format({'border': 1})
        bold_money = workbook.add_format({'num_format': '#,##0.00', 'border': 1, 'bold': True})
        sheet.write(0, 0, _("Retention and Advance Report - %s", self.company_id.name), title)
        sheet.write(1, 0, _("As at %s (amounts in %s)", self.date, self.currency_id.name))
        headers = [
            _("Customer"), _("Project"), _("Total Invoiced"), _("Retention Held"),
            _("Retention Released"), _("Retention Balance"), _("Advance Received"),
            _("Advance Recovered"), _("Advance Balance"),
        ]
        for col, header in enumerate(headers):
            sheet.write(3, col, header, head)
        fields_ = [
            'total_invoiced', 'retention_held', 'retention_released', 'retention_balance',
            'advance_received', 'advance_recovered', 'advance_balance']
        totals = [0.0] * len(fields_)
        row = 4
        for line in self.line_ids:
            sheet.write(row, 0, line.partner_id.display_name, text)
            sheet.write(row, 1, line.sale_order_id.name or '', text)
            for idx, name in enumerate(fields_):
                value = line[name]
                totals[idx] += value
                sheet.write_number(row, 2 + idx, value, money)
            row += 1
        sheet.write(row, 0, _("Total"), head)
        sheet.write(row, 1, '', head)
        for idx, value in enumerate(totals):
            sheet.write_number(row, 2 + idx, value, bold_money)
        sheet.set_column(0, 1, 28)
        sheet.set_column(2, 8, 18)
        workbook.close()
        attachment = self.env['ir.attachment'].create({
            'name': 'Retention_Advance_Report_%s.xlsx' % self.date,
            'type': 'binary',
            'datas': base64.b64encode(output.getvalue()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }


class RaReportLine(models.TransientModel):
    _name = 'ra.report.line'
    _description = 'Retention and Advance Report Line'
    _order = 'partner_id, sale_order_id'

    wizard_id = fields.Many2one('ra.report.wizard', required=True, ondelete='cascade')
    currency_id = fields.Many2one(related='wizard_id.currency_id')
    partner_id = fields.Many2one('res.partner', string='Customer')
    sale_order_id = fields.Many2one('sale.order', string='Project')
    total_invoiced = fields.Monetary(currency_field='currency_id')
    retention_held = fields.Monetary(currency_field='currency_id')
    retention_released = fields.Monetary(currency_field='currency_id')
    retention_balance = fields.Monetary(currency_field='currency_id')
    advance_received = fields.Monetary(currency_field='currency_id')
    advance_recovered = fields.Monetary(currency_field='currency_id')
    advance_balance = fields.Monetary(currency_field='currency_id')
