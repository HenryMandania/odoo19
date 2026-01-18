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
        # staff_ids and product_ids return IDs in read()
        res = self.read(['date_from', 'date_to', 'staff_ids', 'product_ids', 'report_type'])[0]
        return {'form': res}

    def action_print_pdf(self):
        return self.env.ref('merchandizersales.action_report_merchandizer_pdf').report_action(self, data=self._get_report_data())

    def action_review_web(self):
        return self.env.ref('merchandizersales.action_report_merchandizer_web').report_action(self, data=self._get_report_data())