from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    ra_is_advance = fields.Boolean(
        string='Advance Payment', copy=False,
        help="Tick for an advance received from the client before any invoice. "
             "It is also ticked automatically when an invoice recovers from this payment.",
    )
    ra_sale_order_id = fields.Many2one(
        'sale.order', string='Project (Sales Order)', copy=False,
        help="Project this advance belongs to. If empty, it takes the project of the first "
             "invoice that recovers from it.",
    )
    ra_advance_residual = fields.Monetary(
        string='Advance Left', currency_field='currency_id',
        compute='_compute_ra_advance_residual',
    )

    def _ra_open_credit_lines(self):
        """Open credit lines of the payment on the receivable account (the advance)."""
        self.ensure_one()
        return self.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable'
            and not l.reconciled and l.amount_residual < 0
        )

    @api.depends('move_id.line_ids.amount_residual_currency', 'move_id.line_ids.reconciled')
    def _compute_ra_advance_residual(self):
        for payment in self:
            if payment.move_id:
                payment.ra_advance_residual = -sum(
                    payment._ra_open_credit_lines().mapped('amount_residual_currency'))
            else:
                payment.ra_advance_residual = 0.0

    def _ra_available_in(self, currency, date):
        """Amount still available on this advance, expressed in `currency`."""
        self.ensure_one()
        lines = self._ra_open_credit_lines()
        left_company = -sum(lines.mapped('amount_residual'))
        left_payment = -sum(lines.mapped('amount_residual_currency'))
        company_currency = self.company_id.currency_id
        if currency == self.currency_id:
            return left_payment
        if currency == company_currency:
            return left_company
        return company_currency._convert(left_company, currency, self.company_id, date)

    def _ra_available_company(self):
        self.ensure_one()
        return -sum(self._ra_open_credit_lines().mapped('amount_residual'))
