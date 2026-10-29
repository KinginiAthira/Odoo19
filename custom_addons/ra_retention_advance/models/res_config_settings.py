from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ra_retention_account_id = fields.Many2one(
        related='company_id.ra_retention_account_id', readonly=False,
        domain="[('account_type', 'in', ('asset_receivable', 'asset_current', 'asset_non_current'))]",
    )
    ra_default_retention_percent = fields.Float(
        related='company_id.ra_default_retention_percent', readonly=False,
    )
    ra_journal_id = fields.Many2one(
        related='company_id.ra_journal_id', readonly=False,
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
    )
