from odoo import models, fields, api

class MerchandizerReportWizard(models.TransientModel):
    _name = 'sales.staff.report.wizard'
    _description = 'Merchandizer Sales Report Wizard'

    staff_ids = fields.Many2many('x_merchandizer.sales', string='Merchandizers')
    product_ids = fields.Many2many('product.product', string='Products')
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)
    report_type = fields.Selection([
        ('itemized', 'Itemized'),
        ('summary', 'Summary')
    ], string='Report Type', default='itemized', required=True)

    def _get_report_data(self):
        self.ensure_one()
        res = self.read(['date_from', 'date_to', 'staff_ids', 'product_ids', 'report_type'])[0]
        return {'form': res}

    def action_print_pdf(self):
        return self.env.ref('merchandizersales.action_report_merchandizer_pdf').report_action(self, data=self._get_report_data())

    def action_review_web(self):
        return self.env.ref('merchandizersales.action_report_merchandizer_web').report_action(self, data=self._get_report_data())

    def action_view_raw_data(self):
        """Redirects to a filtered list view for standard Odoo CSV export"""
        domain = [
            ('order_id.date_order', '>=', self.date_from),
            ('order_id.date_order', '<=', self.date_to),
            ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
            ('merchandizer_id', '!=', False),
        ]
        if self.staff_ids:
            domain.append(('merchandizer_id', 'in', self.staff_ids.ids))
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))

        return {
            'name': 'Merchandizer Sales Data (Export)',
            'type': 'ir.actions.act_window',
            'res_model': 'pos.order.line',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
        }