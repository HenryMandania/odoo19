from odoo import models, fields


class MemorisedReportsDashboard(models.TransientModel):
    _name = 'memorised.reports.dashboard'
    _description = 'Mavazi Reports Dashboard'
    _rec_name = 'name'

    name = fields.Char(
        string="Name",
        default="Mavazi by Safeway Reports",
        readonly=True
    )

    def action_open_item_sales(self):
        return self.env.ref(
            'mavazi_reports.action_memorised_item_sales_report'
        ).read()[0]

    def action_open_consignment_sales_report(self):
        return self.env.ref(
            'mavaziconsignment.action_consignment_sales_report_wizard'
        ).read()[0]

    def action_open_consignment_returns(self):
        return self.env.ref(
            'mavaziconsignment.action_consignment_return'
        ).read()[0]

    def action_open_merchandizer_sales_report(self):
        return self.env.ref(
            'merchandizersales.action_merchandizer_report_wizard'
        ).read()[0]

    def action_open_vendor_master_list(self):
        return self.env.ref(
            'mavazi_reports.action_vendor_master_list_wizard'
        ).read()[0]