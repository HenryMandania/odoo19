from odoo import models, fields

class CustomerPinReportWizard(models.TransientModel):
    _name = 'customer.pin.report.wizard'
    _description = 'Customer PIN Report Wizard'

    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    customer_id = fields.Many2one('customer.pin.register', string="Customer")

    def _get_report_data(self):
        domain = [('date_order', '>=', self.start_date), ('date_order', '<=', self.end_date)]
        if self.customer_id:
            domain.append(('customer_pin_id', '=', self.customer_id.id))

        orders = self.env['pos.order'].search(domain)
        lines = []
        total_vat = 0.0
        total_amount = 0.0

        for order in orders:
            lines.append({
                'ref': order.name,
                'date': order.date_order.strftime('%Y-%m-%d'),
                'customer_name': order.customer_pin_id.name if order.customer_pin_id else '',
                'vat': order.amount_tax,
                'total': order.amount_total,
            })
            total_vat += order.amount_tax
            total_amount += order.amount_total

        return {
            'lines': lines,
            'totals': {
                'vat': total_vat,
                'total': total_amount,
            },
            'filters': {
                'staff': 'All Merchandizers',
                'records': 'All PIN Records',
            },
            'data': {
                'date_from': self.start_date.strftime('%Y-%m-%d'),
                'date_to': self.end_date.strftime('%Y-%m-%d'),
            },
            'res_company': self.env.company,
        }

    def print_pdf(self):
        return self.env.ref('customerpin.action_customer_pin_report_pdf').report_action(self, data=self._get_report_data())

    def view_web(self):
        return self.env.ref('customerpin.action_customer_pin_report_web').report_action(self, data=self._get_report_data())
