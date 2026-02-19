import logging
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

class MpesaController(http.Controller):

    # -------------------------------------------------------------------------
    # POS → Server: Initiate STK Push
    # -------------------------------------------------------------------------
    @http.route('/mpesa/stk_push', type='json', auth='user', csrf=False, methods=['POST'])
    def stk_push(self, amount, phone, order_name=None):
        """Initiates STK Push via provider."""
        if not order_name:
            _logger.error("STK Push blocked: Missing POS order reference")
            return {'ResponseCode': '1', 'CustomerMessage': 'Missing POS order reference'}

        provider = request.env['mpesa.provider'].sudo().search([], limit=1)
        if not provider:
            _logger.error("STK Push failed: No M-Pesa provider configured.")
            return {'ResponseCode': '1', 'CustomerMessage': 'M-Pesa Provider not configured.'}

        result = provider.trigger_stk_push(amount, phone, order_name)
        _logger.debug("STK Push backend result: %s", result)

        if result and result.get('ResponseCode') == '0':
            _logger.info("STK Push initiated for %s, amount %s, order %s", phone, amount, order_name)
        else:
            _logger.warning("STK Push initiation failed: %s", result)
        return result

    # -------------------------------------------------------------------------
    # POS → Server: Lookup Till/Paybill Transaction
    # -------------------------------------------------------------------------
    @http.route('/mpesa/transaction/lookup', type='json', auth='user', csrf=False, methods=['POST'])
    def lookup(self, amount, pos_ref):
        """Search for a Till/Paybill transaction."""
        trans = request.env['mpesa.transaction'].sudo().search([
            ('amount', '=', amount),
            ('state', '=', 'open'),
            ('mpesa_mode', '=', 'till')
        ], limit=1, order='create_date desc')

        if trans:
            trans.write({
                'state': 'done',
                'pos_reference': pos_ref,
                'order_name': pos_ref,
                'payment_date': fields.Datetime.now()
            })
            
            # Auto-add to POS order
            trans._auto_add_to_pos_order()
            
            _logger.info("Transaction %s closed and auto-added to POS ref %s", trans.id, pos_ref)

            return {
                'success': True,
                'receipt_no': trans.receipt_no or 'N/A',
                'customer_name': trans.customer_name or 'M-Pesa Customer',
                'phone': trans.phone or 'N/A',
                'auto_added': True
            }

        _logger.info("No matching transaction found for amount %s", amount)
        return {'success': False}

    # -------------------------------------------------------------------------
    # Safaricom → Server: Callback for STK Push Results (MAIN FIX)
    # -------------------------------------------------------------------------
    @http.route('/mpesa/callback', type='json', auth='public', csrf=False, methods=['POST'])
    def mpesa_callback(self, **kwargs):
        """Handles Safaricom callback for STK Push results - AUTO-ADDS PAYMENT"""
        try:
            data = request.get_json_data()
            _logger.info("M-Pesa Callback received: %s", data)

            if not data or 'Body' not in data:
                _logger.error("Invalid callback data")
                return {"ResultCode": 1, "ResultDesc": "Invalid data"}

            body = data.get('Body', {}).get('stkCallback', {})
            checkout_id = body.get('CheckoutRequestID')
            result_code = body.get('ResultCode')
            
            if not checkout_id:
                _logger.error("No checkout ID in callback")
                return {"ResultCode": 1, "ResultDesc": "No checkout ID"}

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
                
                # Extract payment details
                receipt = None
                amount_paid = None
                phone = None
                
                for item in items:
                    if item.get('Name') == 'MpesaReceiptNumber':
                        receipt = item.get('Value')
                    elif item.get('Name') == 'Amount':
                        amount_paid = item.get('Value')
                    elif item.get('Name') == 'PhoneNumber':
                        phone = item.get('Value')
                
                # Update transaction
                trans.write({
                    'state': 'done',
                    'receipt_no': receipt,
                    'amount': amount_paid or trans.amount,
                    'phone': str(phone) if phone else trans.phone,
                    'payment_date': fields.Datetime.now()
                })
                
                _logger.info("✅ Transaction %s confirmed. Receipt: %s, Amount: %s", 
                           trans.id, receipt, amount_paid)
                
                # AUTO-ADD PAYMENT TO POS ORDER
                trans._auto_add_to_pos_order()
                
                # Send notification to POS
                trans._send_pos_notification(
                    trans,
                    trans.pos_order_id or request.env['pos.order'],
                    request.env['pos.payment'].sudo().search([
                        ('mpesa_receipt', '=', receipt)
                    ], limit=1)
                )
                
            else:
                # Payment failed
                trans.write({'state': 'failed'})
                _logger.warning("Transaction failed: %s, Checkout: %s", 
                              body.get('ResultDesc'), checkout_id)

            return {"ResultCode": 0, "ResultDesc": "Success"}
            
        except Exception as e:
            _logger.exception("Callback processing error: %s", str(e))
            return {"ResultCode": 1, "ResultDesc": str(e)}