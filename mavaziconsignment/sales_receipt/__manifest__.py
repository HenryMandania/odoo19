{
    'name': 'Sales Receipt',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Display product internal reference in PoS orderlines',
    'author': 'Goonertech ICT Services Ltd',
    'website': 'https://www.goonertech.com', # Optional
    'maintainer': 'Goonertech ICT Services Ltd',
    'email': 'henrymandania9@gmail.com',
    'depends': ['point_of_sale'],
    'assets': {
        'point_of_sale._assets_pos': [
            'sales_receipt/static/src/js/orderline_patch.js',
            'sales_receipt/static/src/xml/orderline_templates.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}