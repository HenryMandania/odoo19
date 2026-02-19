import base64
import requests
import logging
from datetime import datetime
from requests.auth import HTTPBasicAuth

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.http import Controller, route, request

_logger = logging.getLogger(__name__)

# --- Hardcoded sandbox credentials ---
CONSUMER_KEY = "NBdWttxdv29OzT55G0eiQrnYpxdj0VAxbTtnGzurPTn4vKpS"
CONSUMER_SECRET = "mvw7M7fSQIExV4COwCFx8eZQCaCiNe8YLeNi6m95LmDZAHgps9b6X2sIYSZTU40C"
SHORTCODE = "174379"
PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"
CALLBACK_URL = "https://rosalee-curious-earnest.ngrok-free.dev/mpesa/callback"


class MpesaProvider(models.Model):
    _name = 'mpesa.provider'
    _description = 'M-Pesa Payment Provider'

    name = fields.Char(default="M-Pesa Main")
    mpesa_environment = fields.Selection([
        ('sandbox', 'Sandbox'),
        ('production', 'Production')
    ], default='sandbox')
    consumer_key = fields.Char(default=CONSUMER_KEY)
    consumer_secret = fields.Char(default=CONSUMER_SECRET)
    business_shortcode = fields.Char(default=SHORTCODE)
    passkey = fields.Char(default=PASSKEY)
    callback_url = fields.Char(default=CALLBACK_URL)
    transaction_type = fields.Selection([
        ('CustomerPayBillOnline', 'Paybill'),
        ('CustomerBuyGoodsOnline', 'Buy Goods'),
    ], default='CustomerPayBillOnline')

    @api.model
    def trigger_stk_push_from_pos(self, amount, phone, order_name=None):
        """Entry point for POS JavaScript call."""
        _logger.info("POS STK push called: amount=%s, phone=%s, order=%s", amount, phone, order_name)
        return self.trigger_stk_push(amount, phone, order_name)

    def _get_base_url(self):
        return "https://api.safaricom.co.ke" if self.mpesa_environment == 'production' else "https://sandbox.safaricom.co.ke"

    def _get_access_token(self):
        url = f"{self._get_base_url()}/oauth/v1/generate?grant_type=client_credentials"
        try:
            response = requests.get(url, auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET), timeout=10)
            response.raise_for_status()
            token = response.json().get("access_token")
            if not token:
                raise UserError(_("Safaricom did not return an access token."))
            return token
        except Exception as e:
            _logger.error("M-Pesa Auth Error: %s", str(e))
            return None

    def trigger_stk_push(self, amount, phone, order_name=None):
        """Initiate STK push and create transaction record."""
        if not order_name:
            _logger.error("STK Push blocked: Missing POS order reference")
            return {"ResponseCode": "1", "CustomerMessage": "Missing POS order reference"}

        access_token = self._get_access_token()
        if not access_token:
            return {"ResponseCode": "1", "CustomerMessage": "Failed to authenticate with Safaricom"}

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = base64.b64encode(f"{SHORTCODE}{PASSKEY}{timestamp}".encode()).decode("utf-8")

        url = f"{self._get_base_url()}/mpesa/stkpush/v1/processrequest"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        clean_phone = phone.replace("+", "").replace(" ", "")

        payload = {
            "BusinessShortCode": SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(float(amount)),
            "PartyA": clean_phone,
            "PartyB": SHORTCODE,
            "PhoneNumber": clean_phone,
            "CallBackURL": CALLBACK_URL,
            "AccountReference": order_name,
            "TransactionDesc": "POS Payment",
        }

        try:
            res = requests.post(url, json=payload, headers=headers, timeout=30)
            res.raise_for_status()
            res_data = res.json()

            if res_data.get("ResponseCode") == "0":
                self.env['mpesa.transaction'].sudo().create({
                    'checkout_id': res_data.get('CheckoutRequestID'),
                    'amount': amount,
                    'phone': phone,
                    'state': 'open',
                    'mpesa_mode': 'stk',
                    'order_name': order_name,
                    'company_id': self.env.company.id,
                })
                _logger.info("Transaction created for %s, amount %s, order %s", phone, amount, order_name)

            return res_data
        except Exception as e:
            _logger.error("STK Push Exception: %s", str(e))
            return {"ResponseCode": "1", "CustomerMessage": str(e)}


# -------------------------------------------------------------------------
# Callback Controller
# -------------------------------------------------------------------------
# In your controller file, keep this and remove the one in models
route('/mpesa/callback', type='json', auth='public', csrf=False, methods=['POST'])
def mpesa_callback(self):
    """Handles Safaricom callback for STK Push results."""
    try:
        data = request.get_json_data()
        _logger.info("M-Pesa Callback received: %s", data)
        
        if not data or 'Body' not in data:
            _logger.error("Invalid callback data")
            return {"ResultCode": 1, "ResultDesc": "Invalid data"}
        
        body = data.get('Body', {}).get('stkCallback', {})
        checkout_id = body.get('CheckoutRequestID')
        result_code = body.get('ResultCode')
        
        # Find transaction
        trans = request.env['mpesa.transaction'].sudo().search([
            ('checkout_id', '=', checkout_id)
        ], limit=1)
        
        if not trans:
            _logger.error("Transaction not found for checkout_id: %s", checkout_id)
            return {"ResultCode": 1, "ResultDesc": "Transaction not found"}
        
        if result_code == 0:
            # Successful payment
            items = body.get('CallbackMetadata', {}).get('Item', [])
            receipt = next((i.get('Value') for i in items if i.get('Name') == 'MpesaReceiptNumber'), None)
            amount_paid = next((i.get('Value') for i in items if i.get('Name') == 'Amount'), trans.amount)
            phone = next((i.get('Value') for i in items if i.get('Name') == 'PhoneNumber'), trans.phone)
            
            trans.write({
                'state': 'done',
                'receipt_no': receipt,
                'amount': amount_paid,
                'phone': str(phone),
                'payment_date': fields.Datetime.now()
            })
            
            # CRITICAL FIX: Send bus event with proper channel
            if trans.create_uid:
                channel_name = f'pos.mpesa.{trans.create_uid.id}'
                request.env['bus.bus']._sendone(
                    channel_name,
                    'mpesa.payment.confirmed',
                    {
                        'order_name': trans.order_name,
                        'amount': float(amount_paid),
                        'receipt': receipt,
                        'checkout_id': checkout_id
                    }
                )
                _logger.info("Bus event sent to channel: %s", channel_name)
            
            _logger.info("Transaction confirmed: %s, Receipt: %s", trans.id, receipt)
        else:
            trans.write({'state': 'failed'})
            _logger.warning("Transaction failed: %s", body.get('ResultDesc'))
        
        return {"ResultCode": 0, "ResultDesc": "Success"}
        
    except Exception as e:
        _logger.exception("Callback processing error: %s", str(e))
        return {"ResultCode": 1, "ResultDesc": str(e)}