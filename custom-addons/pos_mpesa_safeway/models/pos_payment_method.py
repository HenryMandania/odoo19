from odoo import models, fields, api

class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    @api.model
    def _get_payment_terminal_selection(self):
        """ Manually inject M-Pesa into the selection list """
        res = super()._get_payment_terminal_selection()
        if not any(sel[0] == 'mpesa' for sel in res):
            res.append(('mpesa', 'M-Pesa'))
        return res

    # FIX: Pass the function reference itself, not the string name
    use_payment_terminal = fields.Selection(
        selection=_get_payment_terminal_selection
    )

    mpesa_type = fields.Selection([
        ("stk", "STK Push"),
        ("till", "Till Number")
    ], string="M-Pesa Type", default="stk")

    mpesa_shortcode = fields.Char("M-Pesa Shortcode")
    mpesa_passkey = fields.Char("M-Pesa Passkey")
    mpesa_consumer_key = fields.Char("Consumer Key")
    mpesa_consumer_secret = fields.Char("Consumer Secret")


class MpesaTransaction(models.Model):
    _name = 'mpesa.transaction'
    _description = 'M-Pesa Transaction'
    _order = 'received_at desc'

    trans_id = fields.Char("M-Pesa Code", required=True, index=True)
    name = fields.Char("Customer Name")
    number = fields.Char("Phone Number")
    amount = fields.Float("Amount")
    received_at = fields.Datetime("Received At", default=fields.Datetime.now)
    state = fields.Selection([
        ('available', 'Available'), 
        ('used', 'Used')
    ], default='available')
    
    company_id = fields.Many2one(
        'res.company', 
        required=True, 
        default=lambda self: self.env.company
    )

    # Stick with traditional syntax to avoid registry crashes in your current build
    _sql_constraints = [
        ('unique_trans_id', 'unique(trans_id)', 'The M-Pesa Code must be unique!')
    ]