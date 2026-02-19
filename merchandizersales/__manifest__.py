{
    'name': 'Merchandizer Sales',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'depends': ['point_of_sale', 'sale'],
'data': [
        'security/ir.model.access.csv',
        'views/pos_config_views.xml',
        'views/sales_staff_views.xml',
        'wizard/sales_staff_report_wizard_view.xml',  # Make sure there is a comma here
        'views/sales_staff_actions.xml',
        'reports/sales_staff_report_template.xml',
        'views/sales_staff_report_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'merchandizersales/static/src/js/merchandizer_pos.js',
            'merchandizersales/static/src/xml/merchandizer_window.xml',
            'merchandizersales/static/src/xml/merchandizer_product_screen.xml',
             
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}