{
    'name': 'POS Shortcuts',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_shortcuts/static/src/js/product_shortcuts.js',
            'pos_shortcuts/static/src/js/payment_shortcuts.js',
        ],
    },
    'installable': True,
}