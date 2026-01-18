from odoo import models, fields, api

class MpesaTransaction(models.Model):
    _name = 'mpesa.transaction'
    _description = 'Mpesa Payment Record'
    _order = 'payment_date desc'

    # --- Core Mpesa Data ---
    name = fields.Char(string="Mpesa Code", required=True, index=True)
    phone_number = fields.Char(string="Customer Phone")
    amount = fields.Float(string="Amount Paid")
    ref_number = fields.Char(string="Account Ref / BillRef")
    
    # --- Lifecycle & Consumption Tracking ---
    payment_date = fields.Datetime(
        string="Time/Date Paid", 
        default=fields.Datetime.now, 
        readonly=True
    )
    consumption_date = fields.Datetime(
        string="Time/Date Consumed", 
        readonly=True
    )
    pos_config_id = fields.Many2one(
        'pos.config', 
        string="Consumed by POS", 
        readonly=True
    )
    pos_payment_id = fields.Many2one(
        'pos.payment', 
        string="POS Payment", 
        readonly=True
    )

    state = fields.Selection([
        ('open', 'Open'),      # Payment received, ready to use
        ('closed', 'Closed'),  # Payment validated against a POS order
        ('failed', 'Failed')
    ], default='open', string="Status", index=True)

    # --- Odoo 19 Constraint Syntax ---
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'The Mpesa Code must be unique!')
    ]

    # --- Business Logic ---
    @api.model
    def action_reconcile_payment(self):
        """ Matches Open Mpesa records with pending POS payments. """
        for rec in self.search([('state', '=', 'open')]):
            payment = self.env['pos.payment'].search([
                ('amount', '=', rec.amount),
                ('payment_method_id.name', 'ilike', 'Mpesa'),
                ('pos_order_id.state', '!=', 'cancel'),
                ('is_reconciled', '=', False) # Ensure we don't double-match
            ], limit=1)

            if payment:
                rec.write({
                    'pos_payment_id': payment.id,
                    'pos_config_id': payment.pos_order_id.config_id.id,
                    'consumption_date': fields.Datetime.now(),
                    'state': 'closed'
                })

    def action_consume_from_pos(self, pos_config_id, pos_payment_id=False):
        """ Called from POS frontend to mark transaction as consumed. """
        self.ensure_one()
        return self.write({
            'state': 'closed',
            'pos_config_id': pos_config_id,
            'pos_payment_id': pos_payment_id,
            'consumption_date': fields.Datetime.now()
        })

    @api.model
    def get_open_payments_count(self):
        """ Returns available M-Pesa payments for the POS Header Widget. """
        return self.search_read(
            [('state', '=', 'open')],
            ['name', 'amount', 'payment_date', 'phone_number'],
            order='payment_date desc'
        )