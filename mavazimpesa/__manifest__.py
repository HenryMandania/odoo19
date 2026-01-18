{
    'name': 'Mavazi Mpesa Integration',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Mpesa STK Push and C2B Direct Payments',
    'author': 'Henry Maina',
    'depends': ['base', 'account', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/mpesa_transaction_views.xml',
    ],
    'assets': {
      
        'point_of_sale.assets': [
            'mavazimpesa/static/src/js/product_screen_patch.js',
            'mavazimpesa/static/src/js/mpesa_status_widget.js',
            'mavazimpesa/static/src/xml/mpesa_status_widget.xml',
            'mavazimpesa/static/src/xml/navbar_patch.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}