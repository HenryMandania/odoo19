from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class TransactionLipaNaMpesa(models.Model):
    _name = 'transaction.lipa.na.mpesa'
    _description = 'M-Pesa Payment Transaction'
    _order = 'received_at desc'
    _check_company = True

    trans_id = fields.Char(string="Transaction ID", index=True, copy=False)
    checkout_request_id = fields.Char(string="STK Checkout ID", index=True, copy=False)
    name = fields.Char(string="Customer Name")
    amount = fields.Float(string="Amount", digits=(16, 2))
    number = fields.Char(string="Phone Number")
    received_at = fields.Datetime(string="Received At", default=fields.Datetime.now)
    
    mode = fields.Selection([
        ('stk_push', 'M-Pesa Express (STK)'),
        ('c2b', 'Direct Till/Paybill (C2B)')
    ], string="M-Pesa Mode", default='c2b', required=True)

    company_id = fields.Many2one(
        'res.company', string="Company", required=True, 
        default=lambda self: self.env.company
    )

    pos_config_id = fields.Many2one(
        'pos.config', string="Utilized by Till",
        help="The POS register that reserved or claimed this transaction"
    )

    pos_payment_id = fields.Many2one('pos.payment', string="POS Payment Reference")

    # 🔥 UPDATED STATUS FLOW
    status = fields.Selection([
        ('open', 'Open'),
        ('reserved', 'Reserved'),
        ('closed', 'Closed')
    ], string="Status", default='open', required=True)

    # ==========================
    # 🔐 SAFETY: STATE CONTROL
    # ==========================

    def write(self, vals):
        for rec in self:
            # ❌ Prevent closing already closed transactions
            if rec.status == 'closed' and vals.get('status') == 'closed':
                raise ValidationError(_("Transaction already used."))

            # ❌ Prevent reusing closed transactions
            if rec.status == 'closed' and vals.get('status') != 'closed':
                raise ValidationError(_("Cannot modify a closed transaction."))

            # ❌ Prevent invalid transitions
            if vals.get('status') == 'reserved' and rec.status != 'open':
                raise ValidationError(_("Only open transactions can be reserved."))

            if vals.get('status') == 'closed' and rec.status not in ['open', 'reserved']:
                raise ValidationError(_("Invalid state transition to closed."))

        return super().write(vals)

    # ==========================
    # 🔧 BUSINESS METHODS
    # ==========================

    def action_reserve(self, session_id=False):
        """Used in POS to lock a manual C2B payment to a specific till"""
        for rec in self:
            if rec.status != 'open':
                raise ValidationError(_("Transaction is not available."))

            rec.write({
                'status': 'reserved',
                'pos_config_id': session_id
            })

    def action_close(self):
        """Finalizes the transaction"""
        for rec in self:
            if rec.status == 'closed':
                raise ValidationError(_("Already closed."))

            rec.write({
                'status': 'closed'
            })

    def action_release(self):
        """Unlocks a reserved transaction if the cashier cancels the selection"""
        for rec in self:
            if rec.status == 'reserved':
                rec.write({
                    'status': 'open',
                    'pos_config_id': False
                })

    _sql_constraints = [
        ('unique_trans_id', 'unique(trans_id, company_id)', 'The Transaction ID must be unique per company!'),
    ]