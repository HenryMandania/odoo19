{
    'name': 'M-Pesa Daraja Integration POS 19',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'depends': ['point_of_sale', 'base'],
    'data': [
        'security/ir.model.access.csv',
        'views/mpesa_provider_views.xml',
        'views/mpesa_transaction_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [   
                    "odoo19mpesa/static/src/js/mpesa_payment_patch.js",
                      "odoo19mpesa/static/src/js/components/mpesa_confirmation_dialog.js", 
                      "odoo19mpesa/static/src/scss/mpesa_payment_patch.scss",
        ],
    },
    'installable': True,
    'application': True,
}
