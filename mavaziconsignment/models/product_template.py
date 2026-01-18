from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = "product.template"

    x_is_consignment = fields.Boolean(
        string="Consignment (No Inventory)",
        help="If enabled, purchased on consignment and does not affect stock.",
        default=False
    )

    @api.onchange('x_is_consignment')
    def _onchange_x_is_consignment(self):
        if self.x_is_consignment:
            self.type = 'consu'

    @api.constrains('seller_ids', 'purchase_ok')
    def _check_vendor_mandatory(self):
        for product in self:
            if not product.seller_ids:
                raise ValidationError(
                    _("STRICT VENDOR POLICY: Product '%s' must have at least one vendor assigned.")
                    % product.display_name
                )

    @api.onchange('x_is_consignment')
    def _onchange_x_is_consignment(self):
        for product in self:
            if product.x_is_consignment:
                # Make it consumable automatically
                product.type = 'consu'
                # Disable tracking
                product.tracking = 'none'
            else:
                # Optionally reset to default tracking if unchecked
                product.tracking = 'lot'  # or 'none' depending on your default policy

    