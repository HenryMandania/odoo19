from odoo import http
from odoo.http import request
import requests
import base64
import datetime

class MpesaSTK(http.Controller):

    @http.route('/mpesa/stk_push', type='jsonrpc', auth='user')
    def stk_push(self, phone, amount, method_id):
        method = request.env['pos.payment.method'].sudo().browse(method_id)

        try:
            auth = base64.b64encode(
                f"{method.mpesa_consumer_key}:{method.mpesa_consumer_secret}".encode()
            ).decode()

            token = requests.get(
                "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
                headers={"Authorization": f"Basic {auth}"}
            ).json().get("access_token")

            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

            password = base64.b64encode(
                f"{method.mpesa_shortcode}{method.mpesa_passkey}{timestamp}".encode()
            ).decode()

            payload = {
                "BusinessShortCode": method.mpesa_shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(amount),
                "PartyA": phone,
                "PartyB": method.mpesa_shortcode,
                "PhoneNumber": phone,
                "CallBackURL": f"{request.httprequest.host_url}mpesa/callback",
                "AccountReference": "POS",
                "TransactionDesc": "POS Payment"
            }

            res = requests.post(
                "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers={"Authorization": f"Bearer {token}"}
            ).json()

            return {"success": res.get("ResponseCode") == "0"}

        except Exception as e:
            return {"success": False, "error": str(e)}