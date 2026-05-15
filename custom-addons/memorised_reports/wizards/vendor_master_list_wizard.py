from odoo import models, fields, api


class VendorMasterListWizard(models.TransientModel):
    _name = 'vendor.master.list.wizard'
    _description = 'Vendor Master List Wizard'

    supplier_ids = fields.Many2many(
        'res.partner',
        compute='_compute_supplier_ids'
    )

    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        domain="[('id', 'in', supplier_ids)]"
    )

    @api.depends()
    def _compute_supplier_ids(self):
        supplier_infos = self.env['product.supplierinfo'].search([])
        vendors = supplier_infos.mapped('partner_id')

        if not vendors:
            vendors = self.env['res.partner'].search([
                ('supplier_rank', '>', 0)
            ])

        for rec in self:
            rec.supplier_ids = vendors

    def action_generate_report(self):
        supplier_infos = self.env['product.supplierinfo'].search([
            ('partner_id', '=', self.vendor_id.id)
        ])

        product_templates = supplier_infos.mapped('product_tmpl_id')

        products = self.env['product.product'].search([
            ('product_tmpl_id', 'in', product_templates.ids)
        ])

        return {
            'type': 'ir.actions.act_window',
            'name': 'Vendor Master List',
            'res_model': 'product.product',
            'view_mode': 'list,form',
            'views': [
                (
                    self.env.ref(
                        'memorised_reports.view_vendor_master_list_tree'
                    ).id,
                    'list'
                )
            ],
            'domain': [('id', 'in', products.ids)],
            'target': 'current',
        }