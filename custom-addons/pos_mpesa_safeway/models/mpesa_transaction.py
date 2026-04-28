from odoo import models, fields, api

class MpesaTransaction(models.Model):
    _name = 'mpesa.transaction'
    _description = 'M-Pesa Transaction'

    name = fields.Char("M-Pesa Code", required=True, index=True)
    amount = fields.Float("Amount")
    customer_name = fields.Char("Customer Name")
    phone = fields.Char("Phone")
    state = fields.Selection([
        ('available', 'Available'),
        ('used', 'Used')
    ], default='available')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Transaction already exists')
    ]

    @api.model
    def validate_pos_payment(self, mpesa_code, expected_amount):
        """ Checks if the code exists, is available, and matches the amount """
        transaction = self.search([
            ('name', '=', mpesa_code),
            ('state', '=', 'available'),
            ('amount', '>=', expected_amount)
        ], limit=1)

        if transaction:
            transaction.write({'state': 'used'})
            return {
                'confirmed': True,
                'id': transaction.id,
                'customer': transaction.customer_name
            }
        return {'confirmed': False}