from odoo import models, fields

class TransactionLipaNaMpesa(models.Model):
    _name = 'transaction.lipa.na.mpesa'
    _description = 'M-Pesa Transaction Log'
    _order = 'received_at desc'

    name = fields.Char(string="Customer Name")
    trans_id = fields.Char(string="Transaction ID", index=True)
    amount = fields.Float(string="Amount") # Changed to Float for precision
    number = fields.Char(string="Phone Number")
    received_at = fields.Datetime(string="Received At", default=fields.Datetime.now)
    
    # New Fields
    company_id = fields.Many2one('res.company', string='Company', required=True)
    pos_config_id = fields.Many2one('pos.config', string='POS Terminal')
    status = fields.Selection([
        ('draft', 'Pending'),
        ('done', 'Completed'),
        ('reversed', 'Reversed')
    ], string="Status", default='draft')
    
    # Type to distinguish between Express and C2B
    transaction_type = fields.Selection([
        ('express', 'M-PESA Express'),
        ('c2b', 'Lipa na M-PESA')
    ], string="Type")