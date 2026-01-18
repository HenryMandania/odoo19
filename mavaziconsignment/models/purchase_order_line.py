from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.constrains('product_id', 'partner_id')
    def _check_vendor_policy(self):
        for line in self:
            if not line.product_id:
                continue
            
            # Accessing through product_tmpl_id is safer for custom template fields
            allowed_vendors = line.product_id.product_tmpl_id.seller_ids.mapped('partner_id')

            if not allowed_vendors:
                raise ValidationError(_("STRICT VENDOR POLICY: Product '%s' must have at least one vendor assigned.") % line.product_id.display_name)

            if line.partner_id not in allowed_vendors:
                vendor_names = ', '.join(allowed_vendors.mapped('name'))
                raise ValidationError(_("RESTRICTED ITEM: '%s' can only be purchased from: %s.") % (line.product_id.display_name, vendor_names))

    @api.depends('product_qty', 'move_ids.state', 'move_ids.product_uom_qty')
    def _compute_qty_received(self):
        super()._compute_qty_received()
        for line in self:
            # Change x_is_consignment to is_consignment
            if line.product_id.product_tmpl_id.is_consignment:
                line.qty_received = line.product_qty