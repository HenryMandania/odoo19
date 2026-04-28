import json
import logging
import base64
import datetime
import requests
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class MpesaController(http.Controller):

    @http.route('/mpesa/stk_push', type='jsonrpc', auth='user')
    def stk_push(self, phone, amount, method_id):
        _logger.info("========== MPESA: EXECUTION START ==========")
        method = request.env['pos.payment.method'].sudo().browse(method_id)
        try:
            # Step 1: Auth
            auth_str = f"{method.mpesa_consumer_key}:{method.mpesa_consumer_secret}"
            auth_base64 = base64.b64encode(auth_str.encode()).decode()
            
            token_res = requests.get(
                "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
                headers={"Authorization": f"Basic {auth_base64}"},
                timeout=10
            ).json()
            
            token = token_res.get("access_token")
            if not token:
                return {"success": False, "error": "Invalid M-Pesa Credentials"}

            # Step 2: Payload
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            password = base64.b64encode(f"{method.mpesa_shortcode}{method.mpesa_passkey}{timestamp}".encode()).decode()

            payload = {
                "BusinessShortCode": method.mpesa_shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(float(amount)),
                "PartyA": phone,
                "PartyB": method.mpesa_shortcode,
                "PhoneNumber": phone,
                "CallBackURL": f"{request.httprequest.host_url}mpesa/callback",
                "AccountReference": "POS-Order",
                "TransactionDesc": "POS Payment"
            }

            res = requests.post(
                "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=15
            ).json()

            return {"success": res.get("ResponseCode") == "0", "error": res.get("CustomerMessage")}

        except Exception as e:
            _logger.error("MPESA: Critical STK Error: %s", str(e))
            return {"success": False, "error": "System Error: Check Server Logs"}

    @http.route('/mpesa/check_payment', type='jsonrpc', auth='user')
    def check_payment(self, amount, phone):
        # We search using ilike on the last 9 digits to be safe with 254/07 prefixes
        tx = request.env['mpesa.transaction'].sudo().search([
            ('amount', '=', float(amount)),
            ('number', 'ilike', phone[-9:]), 
            ('state', '=', 'available')
        ], limit=1)

        if tx:
            tx.write({'state': 'used'})
            return {'found': True, 'name': tx.trans_id}
        return {'found': False}

    @http.route('/mpesa/callback', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def mpesa_callback(self):
        _logger.info("MPESA: EXTERNAL CALLBACK DETECTED")
        # In Odoo 19 jsonrpc routes, request.params contains the decoded JSON body
        data = request.params
        stk = data.get('Body', {}).get('stkCallback', {})
        
        if stk and stk.get('ResultCode') == 0:
            items = stk.get('CallbackMetadata', {}).get('Item', [])
            def get_val(name):
                return next((i['Value'] for i in items if i['Name'] == name), None)

            receipt = get_val('MpesaReceiptNumber')
            if receipt:
                request.env['mpesa.transaction'].sudo().create({
                    'trans_id': receipt,
                    'amount': float(get_val('Amount') or 0),
                    'number': str(get_val('PhoneNumber')),
                    'name': 'M-Pesa Customer',
                    'state': 'available'
                })
        return {"ResultCode": 0, "ResultDesc": "Accepted"}