{
    'name': 'POS Shortcuts',
    'version': '1.0',
    'author': 'Goonertech ICT Services, 0728633090',
    'website': 'https://goonertech.co.ke', 
    'category': 'Sales/Point of Sale',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_shortcuts/static/src/js/product_shortcuts.js',
            'pos_shortcuts/static/src/js/payment_shortcuts.js',
            'pos_shortcuts/static/src/js/ReceiptScreen.js',
        ],
    },
    'installable': True,
}