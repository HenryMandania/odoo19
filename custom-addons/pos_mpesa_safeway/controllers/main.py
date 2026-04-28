from odoo import http
from odoo.http import request

class PosMpesaController(http.Controller):

    @http.route('/mpesa/get_available', type='jsonrpc', auth='user')
    def get_available(self, amount):
        company_id = request.env.company.id

        txs = request.env['mpesa.transaction'].sudo().search([
            ('amount', '=', amount),
            ('state', '=', 'available'),
            ('company_id', '=', company_id)
        ])

        return [{
            'id': t.id,
            'name': t.name,
            'customer_name': t.customer_name or 'Customer',
            'phone': t.phone or 'N/A'
        } for t in txs]

    @http.route('/mpesa/mark_used', type='jsonrpc', auth='user')
    def mark_used(self, tx_id, pos_order_name):
        tx = request.env['mpesa.transaction'].sudo().browse(tx_id)

        if tx.exists() and tx.state == 'available':
            pos_order = request.env['pos.order'].sudo().search([
                ('name', '=', pos_order_name)
            ], limit=1)

            tx.write({
                'state': 'used',
                'pos_order_id': pos_order.id if pos_order else False
            })
            return True

        return False
    @http.route('/mpesa/check_payment', type='jsonrpc', auth='user')
    def check_payment(self, amount, phone):
        tx = request.env['mpesa.transaction'].sudo().search([
        ('amount', '=', amount),
        ('phone', '=', phone),
        ('state', '=', 'available')
    ], limit=1)

        if tx:
         tx.write({'state': 'used'})
        return {
            'found': True,
            'name': tx.name
        }

        return {'found': False}