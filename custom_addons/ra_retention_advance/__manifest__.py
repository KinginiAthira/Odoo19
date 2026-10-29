{
    'name': 'Retention and Advance on Customer Invoices',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Retention and advance recovery on progress invoices (contracting, KSA)',
    'description': """
Retention and advance recovery on customer progress invoices.

* Retention held in a separate Retention Receivable account, released later.
* Advance payment recovered automatically from each invoice.
* Credit notes give back retention and advance in proportion.
* Report per customer and project (as at any date) with Excel export.
""",
    'depends': ['account', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'wizard/ra_release_wizard_views.xml',
        'wizard/ra_report_wizard_views.xml',
        'views/res_partner_views.xml',
        'views/menus.xml',
        'report/invoice_report.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
