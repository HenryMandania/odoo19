{
'name': 'Mavazi C-Note (POS Store Credit)',
'version': '1.0.0',
'summary': 'POS Store Credit (C-Note) with partial redemption tracking',
'author': 'Mavazi',
'category': 'Point of Sale',
'depends': [
'point_of_sale',
'stock',
'account',
],
'data': [
'security/ir.model.access.csv',
'views/pos_c_note_views.xml',
'views/pos_payment_method.xml',
],
'assets': {
'point_of_sale._assets_pos': [
'mavazi_c_note/static/src/js/cnote_refund.js',
'mavazi_c_note/static/src/js/cnote_redeem.js',
'mavazi_c_note/static/src/xml/cnote_popup.xml',
],
},
'installable': True,
'application': False,
}