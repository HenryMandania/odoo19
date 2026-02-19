{
    'name': 'Mavazi POS Customization',
    'version': '1.0',
    'depends': ['point_of_sale'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_global_receipt/static/src/xml/pos_receipt_override.xml',
        ],
    },
    'installable': True,
}