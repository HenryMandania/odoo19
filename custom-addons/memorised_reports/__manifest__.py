{
    'name': 'Memorised Reports',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Custom memorised reports for POS sales',
    'author': 'Goonertech ICT Services, 0728633090',
    'website': 'https://goonertech.co.ke',
    'depends': [
        'base',
        'point_of_sale',
        'product',
        'account',
        'mavaziconsignment',
        'merchandizersales',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/item_sales_report_views.xml',
        'views/memorised_reports_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}