{
    'name': 'POS Safaricom',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Integrate your POS with the Safaricom Payment Provider',

    'depends': [
        'point_of_sale','web' 
    ],

'data': [
    'security/ir.model.access.csv',
    'views/pos_payment_method_views.xml',  
    'report/mpesa_report_template.xml',
    'wizard/mpesa_report_wizard_view.xml',  
],

    'assets': {
        'point_of_sale._assets_pos': [
            'pos_safaricom/static/src/**/*',
        ],
        'web.assets_tests': [
            'pos_safaricom/static/tests/tours/**/*',
        ],
    },

    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}