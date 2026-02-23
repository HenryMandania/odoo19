# -*- coding: utf-8 -*-
{
    'name': 'Mavazi Consignment',
    'version': '19.0.1.0.0',
    'summary': 'Manage consignment products with vendor restrictions and automated PO flows.',
    'description': """ Mavazi Consignment Management""",
    'author': 'Henry Maina',
    'website': 'https://www.yourcompany.com',
    'category': 'Inventory/Purchase',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'purchase',
        'stock',
        'point_of_sale',       
        'sale',
         
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/product_views.xml',
        'views/res_partner_views.xml',
        'reports/consignment_return_report.xml',
        'views/consignment_return_views.xml', 
        'views/consignment_sales_report_views.xml',
        'reports/consignment_sales_report_template.xml', 
        'reports/consignment_return_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}