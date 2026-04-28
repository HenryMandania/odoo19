from odoo import models

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _create_picking(self):
        res = super()._create_picking()
        for order in self:
            # Check the template's is_consignment field
            consignment_moves = order.picking_ids.move_ids.filtered(
                lambda m: m.purchase_line_id 
                and m.purchase_line_id.product_id.product_tmpl_id.x_is_consignment
            )
            consignment_moves.unlink()
        return res