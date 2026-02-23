from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = "product.template"

    x_is_consignment = fields.Boolean(
        string="Consignment (No Inventory)",
        help="If enabled, purchased on consignment and does not affect stock.",
        default=False
    )

    @api.constrains('seller_ids', 'purchase_ok')
    def _check_vendor_mandatory(self):
        """Ensures every purchasable product has a vendor assigned."""
        for product in self:
            if product.purchase_ok and not product.seller_ids:
                raise ValidationError(
                    _("STRICT VENDOR POLICY: Product '%s' must have at least one vendor assigned.")
                    % product.display_name
                )

    @api.onchange('x_is_consignment', 'seller_ids')
    def _onchange_consignment_tracking_logic(self):
        """
        Automates Inventory settings:
        - If Consignment + Standard Vendor: Consumable, No Tracking.
        - If Consignment + Inventory Vendor: Storable, Lot Tracking.
        """
        for product in self:
            # Check the custom field from your res_partner.py
            force_tracking = any(s.partner_id.inventory_vendor for s in product.seller_ids if s.partner_id)
            
            if product.x_is_consignment:
                if force_tracking:
                    product.type = 'product'  # Storable Product
                    product.tracking = 'lot'  # By Lots
                else:
                    product.type = 'consu'    # Consumable
                    product.tracking = 'none' # No Tracking
            else:
                # Default back to Storable when consignment is off
                product.type = 'product'