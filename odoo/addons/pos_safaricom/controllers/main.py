# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.tools import verify_hash_signed


class SafaricomController(http.Controller):

    @http.route('/pos_safaricom/callback', type='http', auth='public', methods=['POST'], csrf=False)
    def mpesa_stk_callback(self, payload=None, **kwargs):
        try:
            data = request.get_json_data() or {}

            payload = request.httprequest.args.get('payload')
            decoded_payload = verify_hash_signed(
                request.env["pos.payment.method"].sudo().env,
                "pos_safaricom",
                payload
            )

            payment_method = request.env['pos.payment.method'].sudo().search([
                ('id', '=', decoded_payload.get('payment_method_id')),
            ], limit=1)

            if not payment_method:
                return request.make_json_response({
                    "ResultCode": "1",
                    "ResultDesc": "Payment method not found"
                })

            pos_config_id = decoded_payload.get('pos_config_id')
            stk_callback = data.get('Body', {}).get('stkCallback', {})

            payment_method._notify_stk_callback(
                stk_callback,
                pos_config_id=pos_config_id
            )

            return request.make_json_response({
                "ResultCode": "0",
                "ResultDesc": "Accepted"
            })

        except Exception as e:
            return request.make_json_response({
                "ResultCode": "1",
                "ResultDesc": str(e)
            })

    @http.route('/pos_safaricom/confirmation', type='http', auth='public', methods=['POST'], csrf=False)
    def c2b_confirmation_callback(self, payload=None, **kwargs):
        try:
            data = request.get_json_data() or {}

            decoded_payload = verify_hash_signed(
                request.env["pos.payment.method"].sudo().env,
                "pos_safaricom",
                request.httprequest.args.get('payload')
            )

            payment_method = request.env['pos.payment.method'].sudo().search([
                ('id', '=', decoded_payload.get('payment_method_id')),
            ], limit=1)

            if not payment_method:
                return request.make_json_response({
                    "ResultCode": "C2B00011",
                    "ResultDesc": "Payment method not found"
                })

            if data:
                request.env['transaction.lipa.na.mpesa'].sudo().create({
                    'trans_id': data.get('TransID'),
                    'amount': data.get('TransAmount'),
                    'number': data.get('MSISDN'),
                    'name': f"{data.get('FirstName', '')} {data.get('LastName', '')}".strip() or "C2B Customer",
                    'mode': 'c2b',
                    'status': 'open',
                    'company_id': payment_method.company_id.id,
                })

            return request.make_json_response({
                "ResultCode": "0",
                "ResultDesc": "Accepted"
            })

        except Exception as e:
            return request.make_json_response({
                "ResultCode": "C2B00011",
                "ResultDesc": str(e)
            })