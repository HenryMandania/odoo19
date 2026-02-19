from odoo import models, fields

class PosPayment(models.Model):
    _inherit = 'pos.payment'

    mpesa_bank_ref = fields.Char(
        string="M-Pesa Bank Reference",
        help="Stores the M-Pesa receipt code for this payment"
    )
