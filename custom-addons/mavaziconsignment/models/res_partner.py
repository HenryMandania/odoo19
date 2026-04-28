from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    inventory_vendor = fields.Boolean(
        string="Inventory Vendor",
        help="If enabled, consignment items from this vendor will track stock levels.",
        default=False
    )