# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import requests
import logging
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import hash_sign

_logger = logging.getLogger(__name__)
TIMEOUT = 30

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    consumer_key = fields.Char(string="Consumer Key")
    consumer_secret = fields.Char(string="Consumer Secret")
    business_short_code = fields.Char(string="Business Short Code")
    passkey = fields.Char(string="Passkey")
    safaricom_test_mode = fields.Boolean(string="Test Mode", default=True)
    safaricom_payment_type = fields.Selection(
        selection=[('mpesa_express', 'M-PESA Express'), ('lipa_na_mpesa', 'Lipa na M-PESA')],
        string="Payment Type",
        default='mpesa_express',
    )

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('safaricom', 'M-Pesa')]

    @api.model_create_multi
    def create(self, vals_list):
        payment_methods = super().create(vals_list)
        for payment_method in payment_methods:
            if (payment_method.use_payment_terminal == 'safaricom' and 
                payment_method.safaricom_payment_type == 'lipa_na_mpesa'):
                payment_method.lipa_na_mpesa_register_urls()
        return payment_methods

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['safaricom_test_mode', 'safaricom_payment_type', 'business_short_code']
        return params

    def _get_express_stkpush_endpoint(self):
        return 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest' if self.safaricom_test_mode else \
               'https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest'

    def _get_oauth_endpoint(self):
        return 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials' if self.safaricom_test_mode else \
               'https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'

    def _get_lipa_na_mpesa_register_endpoint(self):
        return 'https://sandbox.safaricom.co.ke/mpesa/c2b/v2/registerurl' if self.safaricom_test_mode else \
               'https://api.safaricom.co.ke/mpesa/c2b/v2/registerurl'

    def _get_qr_code_endpoint(self):
        return 'https://sandbox.safaricom.co.ke/mpesa/qrcode/v1/generate' if self.safaricom_test_mode else \
               'https://api.safaricom.co.ke/mpesa/qrcode/v1/generate'

    def _get_bearer_token(self):
        self.ensure_one()
        if not self.consumer_key or not self.consumer_secret:
            raise UserError(_("Credentials are required for Safaricom M-Pesa"))
        try:
            auth = requests.auth.HTTPBasicAuth(self.consumer_key.strip(), self.consumer_secret.strip())
            response = requests.get(self._get_oauth_endpoint(), auth=auth, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json().get('access_token')
        except Exception:
            raise UserError(_("Failed to retrieve access token from Safaricom"))

    def _get_password(self, timestamp):
        return base64.b64encode(f"{self.business_short_code}{self.passkey}{timestamp}".encode()).decode()

    def _format_phone_number(self, phone):
        phone = ''.join(filter(str.isdigit, phone)).lstrip('0')
        if not phone.startswith('254'):
            phone = '254' + phone
        return phone

    def mpesa_express_send_payment_request(self, data):
        self.ensure_one()
        try:
            access_token = self._get_bearer_token()
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = self._get_password(timestamp)
            phone_number = self._format_phone_number(data.get('phone_number', ''))

            signed_payload = hash_sign(
                self.sudo().env, 
                "pos_safaricom", 
                {
                    "payment_method_id": self.id,
                    "pos_config_id": data.get('pos_config_id')
                }, 
                expiration_hours=6
            )

            payload = {
                'BusinessShortCode': self.business_short_code,
                'Password': password,
                'Timestamp': timestamp,
                'TransactionType': 'CustomerPayBillOnline',
                'Amount': int(float(data.get('amount', 0))),
                'PartyA': phone_number,
                'PartyB': self.business_short_code,
                'PhoneNumber': phone_number,
                'CallBackURL': f"{self.get_base_url()}/pos_safaricom/callback?payload={signed_payload}",
                'AccountReference': data.get('account_reference', 'POS Payment'),
                'TransactionDesc': 'Payment',
            }

            response = requests.post(self._get_express_stkpush_endpoint(), json=payload,
                                     headers={'Authorization': f'Bearer {access_token}'}, timeout=TIMEOUT)
            result = response.json()

            if result.get('ResponseCode') == '0':
                return {
                    'success': True, 
                    'checkout_request_id': result.get('CheckoutRequestID'),
                    'merchant_request_id': result.get('MerchantRequestID')
                }

            return {'error': result.get('errorMessage', 'Push Request Failed')}
        except Exception as e:
            return {'error': str(e)}

    def _notify_stk_callback(self, stk_callback, pos_config_id=False):
        self.ensure_one()

        res_code = stk_callback.get('ResultCode')
        checkout_id = stk_callback.get('CheckoutRequestID')
        merchant_id = stk_callback.get('MerchantRequestID')

        payment_successful = (res_code == 0)
        transaction_id = False
        phone_number = False

        if payment_successful:
            callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])

            meta = {
                item.get('Name'): item.get('Value')
                for item in callback_metadata
                if item.get('Name')
            }

            mpesa_id = meta.get('MpesaReceiptNumber')
            phone_number = meta.get('PhoneNumber')

            if mpesa_id:
                existing = self.env['transaction.lipa.na.mpesa'].sudo().search([
                    ('trans_id', '=', mpesa_id)
                ], limit=1)

                if not existing:
                    new_tx = self.env['transaction.lipa.na.mpesa'].sudo().create({
                        'trans_id': mpesa_id,
                        'checkout_request_id': checkout_id,
                        'number': str(phone_number) if phone_number else False,
                        'amount': float(meta.get('Amount') or 0.0),
                        'status': 'closed',
                        'mode': 'stk_push',
                        'name': 'STK Push Online',
                        'company_id': self.company_id.id,
                        'received_at': fields.Datetime.now(),
                        'pos_config_id': pos_config_id,
                    })
                    transaction_id = new_tx.trans_id
                else:
                    transaction_id = existing.trans_id

                    if pos_config_id and not existing.pos_config_id:
                        existing.sudo().write({'pos_config_id': pos_config_id})

        notification_data = {
            'checkout_request_id': checkout_id,
            'merchant_request_id': merchant_id,
            'success': payment_successful,
            'transaction_id': transaction_id,
            'phone_number': phone_number,
            'payment_method_id': self.id,
            'result_desc': stk_callback.get('ResultDesc', ''),
        }

        bus = self.env['bus.bus'].sudo()

        if pos_config_id:
            channel = f"pos_config_{pos_config_id}"
            bus._sendone(channel, 'SAFARICOM_LATEST_RESPONSE', notification_data)
        else:
            sessions = self.env['pos.session'].sudo().search([
                ('state', '=', 'opened'),
                ('config_id.payment_method_ids', 'in', self.ids)
            ])

            for session in sessions:
                channel = f"pos_config_{session.config_id.id}"
                bus._sendone(channel, 'SAFARICOM_LATEST_RESPONSE', notification_data)

        return True

    def reserve_transaction(self, transaction_id, pos_config_id):
        transaction = self.env['transaction.lipa.na.mpesa'].browse(transaction_id)
        transaction.sudo().action_reserve(session_id=pos_config_id)
        return True

    def mark_transaction_used(self, transaction_id, pos_payment_id=False, pos_config_id=False):
        self.ensure_one()
        transaction = self.env['transaction.lipa.na.mpesa'].browse(transaction_id)
        transaction.sudo().write({
            'pos_payment_id': pos_payment_id,
            'pos_config_id': pos_config_id or transaction.pos_config_id.id,
        })
        transaction.sudo().action_close()
        return True

    def generate_qr_code(self, data):
        self.ensure_one()
        try:
            access_token = self._get_bearer_token()
            body = {
                'MerchantName': data.get('name', self.company_id.name),
                'RefNo': data.get('ref', 'POS-Order'),
                'Amount': data.get('amount', 0),
                'TrxCode': data.get('trxCode', 'BG'),
                'CPI': data.get('cpi', self.business_short_code),
                'Size': data.get('size', '300'),
            }
            headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
            response = requests.post(self._get_qr_code_endpoint(), json=body, headers=headers, timeout=TIMEOUT)
            result = response.json()
            qr_code = result.get('QRCode')
            if not qr_code:
                return {'error': result.get('errorMessage', 'No QR Code in Safaricom response')}
            return qr_code
        except Exception as e:
            return {'error': str(e)}

    def lipa_na_mpesa_register_urls(self):
        self.ensure_one()
        try:
            access_token = self._get_bearer_token()
            signed_payload = hash_sign(self.sudo().env, "pos_safaricom", {"payment_method_id": self.id}, expiration_hours=6)
            payload = {
                'ShortCode': self.business_short_code,
                'ResponseType': 'Completed',
                'ValidationURL': f"{self.get_base_url()}/pos_safaricom/validation?payload={signed_payload}",
                'ConfirmationURL': f"{self.get_base_url()}/pos_safaricom/confirmation?payload={signed_payload}",
            }
            requests.post(self._get_lipa_na_mpesa_register_endpoint(), json=payload,
                          headers={'Authorization': f'Bearer {access_token}'}, timeout=TIMEOUT)
        except Exception:
            _logger.error("Failed to register M-Pesa C2B URLs")