import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class MpesaTransaction(models.Model):
    _name = 'mpesa.transaction'
    _description = 'M-Pesa Transaction'
    _order = 'create_date desc'

    # -------------------------------------------------------------------------
    # Core Fields
    # -------------------------------------------------------------------------
    checkout_id = fields.Char("Checkout Request ID", index=True)
    amount = fields.Float("Amount", required=True)
    phone = fields.Char("Phone Number", index=True)
    receipt_no = fields.Char("M-Pesa Receipt", help="Mpesa confirmation code")
    customer_name = fields.Char("Customer Name")
    payment_date = fields.Datetime("Payment Date and Time")

    mpesa_mode = fields.Selection([
        ('stk', 'STK Push'),
        ('till', 'Till/C2B')
    ], string="M-Pesa Mode", default='stk', required=True)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    pos_reference = fields.Char("POS Reference")
    order_name = fields.Char("POS Order Reference")
    pos_order_id = fields.Many2one('pos.order', string="POS Order")

    state = fields.Selection([
        ('open', 'Open'),
        ('done', 'Done'),
        ('failed', 'Failed')
    ], default='open', required=True)

    # -------------------------------------------------------------------------
    # Main Method: Automatically add payment to POS order on confirmation
    # -------------------------------------------------------------------------
    def _auto_add_to_pos_order(self):
        """
        Automatically add payment to POS order when transaction is confirmed
        Called from callback or when transaction state changes to 'done'
        """
        for transaction in self:
            if transaction.state != 'done' or not transaction.order_name:
                continue
                
            # Find the POS order
            pos_order = self.env['pos.order'].sudo().search([
                ('pos_reference', '=', transaction.order_name)
            ], limit=1)
            
            if not pos_order:
                _logger.warning(f"POS order not found: {transaction.order_name}")
                continue
                
            # Find M-Pesa payment method
            payment_method = self.env['pos.payment.method'].sudo().search([
                ('name', 'ilike', 'M-Pesa'),
                ('company_id', '=', transaction.company_id.id)
            ], limit=1)
            
            if not payment_method:
                _logger.error(f"M-Pesa payment method not found for company {transaction.company_id.id}")
                continue
                
            # Check if payment already exists
            existing_payment = self.env['pos.payment'].sudo().search([
                ('pos_order_id', '=', pos_order.id),
                ('mpesa_receipt', '=', transaction.receipt_no)
            ])
            
            if existing_payment:
                _logger.info(f"Payment already exists for receipt {transaction.receipt_no}")
                continue
                
            # Create the payment
            try:
                payment_data = {
                    'pos_order_id': pos_order.id,
                    'amount': transaction.amount,
                    'payment_method_id': payment_method.id,
                    'mpesa_receipt': transaction.receipt_no,
                    'mpesa_phone': transaction.phone,
                    'mpesa_customer_name': transaction.customer_name,
                    'mpesa_checkout_id': transaction.checkout_id,
                    'payment_date': transaction.payment_date or fields.Datetime.now(),
                }
                
                payment = self.env['pos.payment'].sudo().create(payment_data)
                
                # Update order state if needed
                if pos_order.state == 'draft':
                    pos_order.write({'state': 'paid'})
                
                # Link transaction to order
                transaction.pos_order_id = pos_order.id
                transaction.pos_reference = pos_order.pos_reference
                
                _logger.info(f"✅ Payment automatically added to order {pos_order.pos_reference}")
                _logger.info(f"   Amount: {transaction.amount}, Receipt: {transaction.receipt_no}")
                
                # Send bus notification
                self._send_pos_notification(transaction, pos_order, payment)
                
            except Exception as e:
                _logger.error(f"Failed to create payment for order {pos_order.pos_reference}: {str(e)}")

    def _send_pos_notification(self, transaction, pos_order, payment):
        """Send real-time notification to POS frontend"""
        bus_data = {
            'type': 'mpesa_payment_auto_added',
            'order_name': transaction.order_name,
            'order_reference': pos_order.pos_reference,
            'order_id': pos_order.id,
            'amount': transaction.amount,
            'receipt': transaction.receipt_no,
            'receipt_no': transaction.receipt_no,
            'MpesaReceiptNumber': transaction.receipt_no,
            'phone': transaction.phone,
            'customer_name': transaction.customer_name or 'Customer',
            'checkout_id': transaction.checkout_id,
            'payment_id': payment.id,
            'payment_method': payment.payment_method_id.name,
            'timestamp': fields.Datetime.now().isoformat(),
            'message': 'Payment automatically added to order',
        }
        
        # Send to global POS channel
        self.env['bus.bus']._sendone('pos', 'mpesa.auto.payment', bus_data)
        _logger.info(f"📢 Bus notification sent for order {pos_order.pos_reference}")

    # -------------------------------------------------------------------------
    # Override write method to trigger auto-add when state changes to done
    # -------------------------------------------------------------------------
    def write(self, vals):
        result = super().write(vals)
        
        # If state changed to 'done', auto-add to POS order
        if 'state' in vals and vals['state'] == 'done':
            self._auto_add_to_pos_order()
            
        return result

    # -------------------------------------------------------------------------
    # STK Status Check Method (Updated)
    # -------------------------------------------------------------------------
    @api.model
    def check_stk_status(self, checkout_id, order_ref):
        """
        Check status of STK push transaction
        Args:
            checkout_id (str): Checkout Request ID
            order_ref (str): POS order reference
        Returns:
            dict: Transaction status
        """
        _logger.info(f"🔍 Checking STK status: checkout_id={checkout_id}, order={order_ref}")
        
        trans = self.sudo().search([
            ('checkout_id', '=', checkout_id),
            ('mpesa_mode', '=', 'stk')
        ], limit=1)
        
        if not trans:
            return {
                'success': False,
                'message': 'Transaction not found',
                'status': 'not_found'
            }
        
        # If transaction is done, ensure it's linked to order
        if trans.state == 'done':
            if not trans.pos_reference:
                trans.pos_reference = order_ref
                trans.order_name = order_ref
                trans._auto_add_to_pos_order()
            
            # Send notification
            trans._send_pos_notification(
                trans,
                trans.pos_order_id or self.env['pos.order'],
                self.env['pos.payment'].sudo().search([
                    ('mpesa_receipt', '=', trans.receipt_no)
                ], limit=1)
            )
        
        result = {
            'success': trans.state == 'done',
            'status': trans.state,
            'receipt_no': trans.receipt_no or '',
            'amount': trans.amount,
            'phone': trans.phone,
            'customer_name': trans.customer_name,
            'order_name': trans.order_name,
            'pos_order_id': trans.pos_order_id.id if trans.pos_order_id else None,
            'auto_added': trans.pos_order_id is not None
        }
        
        _logger.info(f"📊 STK status result: {result}")
        return result

    # -------------------------------------------------------------------------
    # Lookup Method (Updated to auto-add)
    # -------------------------------------------------------------------------
    @api.model
    def lookup(self, amount, pos_ref, phone=None):
        """
        Lookup M-Pesa transaction for POS
        Args:
            amount (float): Amount to lookup
            pos_ref (str): POS order reference
            phone (str, optional): Phone number for STK transactions
        Returns:
            dict: Transaction details or failure message
        """
        _logger.info(f"🔍 M-Pesa lookup called: amount={amount}, pos_ref={pos_ref}, phone={phone}")
        
        mode = 'stk' if phone else 'till'
        domain = [
            ('amount', '=', float(amount)),
            ('state', '=', 'open'),
            ('mpesa_mode', '=', mode)
        ]
        
        if mode == 'stk' and phone:
            domain.append(('phone', '=', phone))
        
        trans = self.sudo().search(domain, limit=1, order='create_date desc')
        
        if trans:
            # Mark as done and auto-add to order
            trans.write({
                'state': 'done',
                'pos_reference': pos_ref,
                'order_name': pos_ref,
                'payment_date': fields.Datetime.now()
            })
            
            # Auto-add to POS order
            trans._auto_add_to_pos_order()
            
            _logger.info(f"✅ Transaction {trans.id} found, closed, and auto-added to POS ref {pos_ref}")
            
            return {
                'success': True,
                'receipt_no': trans.receipt_no or 'N/A',
                'customer_name': trans.customer_name or 'M-Pesa Customer',
                'phone': trans.phone or 'N/A',
                'amount': trans.amount,
                'transaction_id': trans.id,
                'checkout_id': trans.checkout_id,
                'auto_added': True,
                'pos_order_id': trans.pos_order_id.id if trans.pos_order_id else None
            }
        
        _logger.info(f"❌ No matching transaction found: amount={amount}, pos_ref={pos_ref}, phone={phone}")
        return {
            'success': False,
            'message': 'No matching open transaction found'
        }