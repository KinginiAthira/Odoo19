from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class RaReleaseWizard(models.TransientModel):
    _name = 'ra.release.wizard'
    _description = 'Release Retention'

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    sale_order_id = fields.Many2one(
        'sale.order', string='Project',
        help="Optional. Show only the invoices of this project.")
    date = fields.Date(
        string='Release Date', required=True, default=fields.Date.context_today,
        help="Date of the entry. The released amount becomes due on this date.")
    line_ids = fields.One2many(
        'ra.release.wizard.line', 'wizard_id', string='Invoices',
        compute='_compute_line_ids', store=True, readonly=False)

    @api.depends('partner_id', 'sale_order_id', 'company_id')
    def _compute_line_ids(self):
        for wizard in self:
            commands = [Command.clear()]
            if wizard.partner_id:
                domain = [
                    ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('company_id', '=', wizard.company_id.id),
                    ('commercial_partner_id', '=', wizard.partner_id.commercial_partner_id.id),
                ]
                if wizard.sale_order_id:
                    domain.append(('ra_sale_order_id', '=', wizard.sale_order_id.id))
                invoices = self.env['account.move'].search(domain, order='invoice_date, id')
                totals = invoices._ra_type_totals()
                for invoice in invoices:
                    data = totals[invoice.id]
                    balance = data['transfer'] - data['return'] - data['release']
                    if invoice.currency_id.compare_amounts(balance, 0.0) > 0:
                        commands.append(Command.create({
                            'invoice_id': invoice.id,
                            'retention_balance': balance,
                            'amount': balance,
                        }))
            wizard.line_ids = commands

    def action_release(self):
        self.ensure_one()
        lines = self.line_ids.filtered(lambda l: l.amount)
        if not lines:
            raise UserError(_("There is nothing to release."))
        if not self.company_id.ra_retention_account_id:
            raise UserError(_("Please choose the Retention Receivable account in the settings."))
        entries = self.env['account.move']
        for line in lines:
            invoice = line.invoice_id
            currency = invoice.currency_id
            if invoice.company_id != self.company_id:
                raise UserError(_("%s belongs to another company.", invoice.name))
            if currency.compare_amounts(line.amount, 0.0) < 0:
                raise UserError(_("The amount to release cannot be negative."))
            data = invoice._ra_type_totals()[invoice.id]
            balance = data['transfer'] - data['return'] - data['release']
            if currency.compare_amounts(line.amount, balance) > 0:
                raise UserError(_(
                    "You cannot release more than the retention balance of %(invoice)s (%(balance)s).",
                    invoice=invoice.name, balance=balance))
            receivable = invoice._ra_receivable_lines()[:1]
            label = _("Retention release - %s", invoice.name)
            entries |= invoice._ra_make_entry('release', self.date, [
                invoice._ra_line(receivable.account_id, line.amount, label, debit=True,
                                 partner=receivable.partner_id, date_maturity=self.date),
                invoice._ra_line(invoice.company_id.ra_retention_account_id, line.amount, label,
                                 debit=False, partner=receivable.partner_id),
            ], amount=line.amount, label=label)
        return {
            'type': 'ir.actions.act_window',
            'name': _("Retention Release Entries"),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', entries.ids)],
        }


class RaReleaseWizardLine(models.TransientModel):
    _name = 'ra.release.wizard.line'
    _description = 'Release Retention Line'

    wizard_id = fields.Many2one('ra.release.wizard', required=True, ondelete='cascade')
    invoice_id = fields.Many2one('account.move', string='Invoice', required=True)
    project_id = fields.Many2one(related='invoice_id.ra_sale_order_id', string='Project')
    currency_id = fields.Many2one(related='invoice_id.currency_id')
    retention_balance = fields.Monetary(string='Retention Balance', currency_field='currency_id')
    amount = fields.Monetary(string='Amount to Release', currency_field='currency_id')
