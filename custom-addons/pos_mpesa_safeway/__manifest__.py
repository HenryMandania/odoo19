{
    'name': 'M-Pesa POS Integration for Safeway',
    'version': '19.0.1.0',
    'category': 'Sales/Point of Sale',
    'author': 'Goonertech ICT Services, 0728633090',
    'website': 'https://goonertech.co.ke', 
    'depends': [
        'point_of_sale',
        'account',
        'base',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',      
        'views/mpesa_transaction_views.xml',  
        'views/pos_payment_method_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_mpesa_safeway/static/src/js/payment_mpesa.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}