from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    ra_retention_account_id = fields.Many2one(
        'account.account',
        string='Retention Receivable Account',
        domain="[('account_type', 'in', ('asset_receivable', 'asset_current', 'asset_non_current'))]",
        help="Account where the retention held by the client is kept until handover. "
             "Use a separate asset account (not the normal receivable account).",
    )
    ra_default_retention_percent = fields.Float(
        string='Default Retention %', default=10.0, digits=(5, 2),
    )
    ra_journal_id = fields.Many2one(
        'account.journal',
        string='Retention and Advance Journal',
        domain="[('type', '=', 'general')]",
        help="Miscellaneous journal used for the entries created by this module. "
             "If empty, the first miscellaneous journal of the company is used.",
    )
