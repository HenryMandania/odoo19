import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class MpesaController(http.Controller):

    # FIX: type='json' is now type='jsonrpc' in Odoo 19
    @http.route('/payment/mpesa/callback', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def mpesa_callback(self, **post):
        """
        Unified Callback: Handles both C2B Direct Payments and STK Push Results.
        """
        # In Odoo 19 type='jsonrpc', parameters are passed directly in **post or via request.params
        data = request.get_json_data()
        _logger.info("Mpesa Callback Received: %s", json.dumps(data))

        # 1. Handle STK Push / Lipa na Mpesa Online
        if 'Body' in data:
            stk_result = data['Body']['stkCallback']
            if stk_result.get('ResultCode') == 0:
                metadata = {item['Name']: item.get('Value') for item in stk_result['CallbackMetadata']['Item']}
                
                request.env['mpesa.transaction'].sudo().create({
                    'name': metadata.get('MpesaReceiptNumber'),
                    'phone_number': str(metadata.get('PhoneNumber')),
                    'amount': float(metadata.get('Amount')),
                    'ref_number': stk_result.get('CheckoutRequestID'),
                    'state': 'open' # Keep as 'open' so POS polling can find it
                })
            return {"ResultCode": 0, "ResultDesc": "STK Result Processed"}

        # 2. Handle C2B Direct Payment
        trans_id = data.get('TransID')
        if trans_id:
            request.env['mpesa.transaction'].sudo().create({
                'name': trans_id,
                'phone_number': data.get('MSISDN'),
                'amount': float(data.get('TransAmount')),
                'ref_number': data.get('BillRefNumber'),
                'state': 'open' # Keep as 'open' for POS consumption
            })
            return {"ResultCode": 0, "ResultDesc": "C2B Payment Processed"}

        return {"ResultCode": 1, "ResultDesc": "Unknown Format"}

    @http.route('/payment/mpesa/validate', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def mpesa_validation(self, **post):
        """ Safaricom calls this BEFORE accepting a C2B payment to verify the BillRef. """
        data = request.get_json_data()
        bill_ref = data.get('BillRefNumber')
        
        # Retail Speed: We accept all payments to avoid customer frustration at the till,
        # but you can toggle this to check for active POS orders if needed.
        return {"ResultCode": 0, "ResultDesc": "Accepted"}
        
    @http.route('/pos/mpesa/poll_payment', type='jsonrpc', auth='user')
    def poll_mpesa_payment(self, amount):
        """
        Used by the POS JS to find an available payment.
        """
        # Optimized for high-speed retail: Find latest open payment matching the amount
        transaction = request.env['mpesa.transaction'].sudo().search([
            ('amount', '=', float(amount)),
            ('state', '=', 'open')
        ], limit=1, order='payment_date desc')

        if transaction:
            return {
                'id': transaction.id,
                'name': transaction.name,
                'amount': transaction.amount,
                'phone': transaction.phone_number
            }
        return False