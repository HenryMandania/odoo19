from odoo import models, fields, api
from datetime import datetime, time

class MpesaReportWizard(models.TransientModel):
    _name = 'mpesa.report.wizard'
    _description = 'MPESA Report Wizard'

    # Changed from Datetime to Date
    date_from = fields.Date(string="Start Date", required=True)
    date_to = fields.Date(string="End Date", required=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    status = fields.Selection([('open', 'Open'), ('closed', 'Closed')], string="Status")

    def _get_domain(self):
        """ Helper to build the domain with time boundaries """
        # Start of the day (00:00:00)
        dt_from = datetime.combine(self.date_from, time.min)
        # End of the day (23:59:59)
        dt_to = datetime.combine(self.date_to, time.max)

        domain = [
            ('received_at', '>=', dt_from),
            ('received_at', '<=', dt_to),
            ('company_id', '=', self.company_id.id),
        ]
        if self.status:
            domain.append(('status', '=', self.status))
        return domain

    def get_report_data(self):
        return self.env['transaction.lipa.na.mpesa'].search(self._get_domain())

    def action_print_pdf(self):
        return self.env.ref('pos_safaricom.action_mpesa_report_pdf').report_action(self)

    def action_view_html(self):
        return self.env.ref('pos_safaricom.action_mpesa_report_html').report_action(self)

    def action_print_excel(self):
        return {
            'name': 'MPESA Transactions Export',
            'type': 'ir.actions.act_window',
            'res_model': 'transaction.lipa.na.mpesa',
            'view_mode': 'list',
            'views': [(self.env.ref('pos_safaricom.view_transaction_mpesa_list').id, 'list')],
            'domain': self._get_domain(),
            'target': 'current',
        }