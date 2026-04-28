from odoo import models, fields, api

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    vendor_id = fields.Many2one(
        'res.partner',
        string="Vendor",
        compute="_compute_vendor_id",
        store=True,
        readonly=True
    )

    @api.depends('product_id')
    def _compute_vendor_id(self):
        # Changed 'for line in line' to 'for line in self'
        for line in self:
            if line.product_id and line.product_id.seller_ids:
                # Assigns the first vendor found in the product's Purchase tab
                line.vendor_id = line.product_id.seller_ids[0].partner_id
            else:
                line.vendor_id = False