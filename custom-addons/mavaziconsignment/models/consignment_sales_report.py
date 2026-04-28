# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ConsignmentSalesReportWizard(models.TransientModel):
    _name = 'consignment.sales.report.wizard'
    _description = 'Wizard for Consignment Sales Report'

    date_from = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    vendor_id = fields.Many2one('res.partner', string='Vendor', domain="[('supplier_rank','>',0)]")
    product_id = fields.Many2one('product.product', string='Product', domain="[('x_is_consignment','=',True)]")
    
    output_type = fields.Selection([
        ('pdf', 'PDF Report'),
        ('web', 'Web View (HTML)'),
        ('excel', 'Excel')
    ], string='Output Format', default='pdf', required=True)

    def action_print_report(self):
        domain = [
            ('order_id.date_order', '>=', self.date_from),
            ('order_id.date_order', '<=', self.date_to),
            ('product_id.x_is_consignment', '=', True),
            ('order_id.state', 'in', ['paid', 'done', 'invoiced'])
        ]
        
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        if self.vendor_id:
            domain.append(('product_id.seller_ids.partner_id', '=', self.vendor_id.id))

        lines = self.env['pos.order.line'].search(domain)
        
        # Handle Excel Output via Native List View
        if self.output_type == 'excel':
            # Clear previous results for this user
            self.env['consignment.sales.report.line.temp'].search([('create_uid', '=', self.env.user.id)]).unlink()
            
            vals_list = []
            for line in lines:
                vendor = line.product_id.seller_ids[0].partner_id if line.product_id.seller_ids else False
                vals_list.append({
                    'vendor_name': vendor.name if vendor else 'No Vendor',
                    'item_number': line.product_id.default_code or '',
                    'item_name': line.product_id.name,
                    'qty_sold': line.qty,
                    'net_sales': line.price_subtotal,
                    'vat_amount': line.price_subtotal_incl - line.price_subtotal,
                    'gross_amount': line.price_subtotal_incl,
                })
            
            self.env['consignment.sales.report.line.temp'].create(vals_list)
            
            return {
                'name': 'Consignment Sales (Excel Ready)',
                'type': 'ir.actions.act_window',
                'res_model': 'consignment.sales.report.line.temp',
                'view_mode': 'list',
                'target': 'current',
                'domain': [('create_uid', '=', self.env.user.id)],
            }

        # PDF/Web Logic
        data_lines = []
        totals = {'qty_sold': 0, 'net_sales': 0.0, 'vat_amount': 0.0, 'gross_amount': 0.0}
        for line in lines:
            net = line.price_subtotal
            gross = line.price_subtotal_incl
            vendor = line.product_id.seller_ids[0].partner_id if line.product_id.seller_ids else False
            data_lines.append({
                'vendor_name': vendor.name if vendor else 'No Vendor',
                'item_number': line.product_id.default_code or '',
                'item_name': line.product_id.name,
                'qty_sold': line.qty,
                'net_sales': net,
                'vat_amount': gross - net,
                'gross_amount': gross,
            })
            totals['qty_sold'] += line.qty
            totals['net_sales'] += net
            totals['vat_amount'] += (gross - net)
            totals['gross_amount'] += gross

        report_data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'vendor': self.vendor_id.name if self.vendor_id else 'All Vendors',
            'product': self.product_id.name if self.product_id else 'All Products',
            'lines': data_lines,
            'totals': totals,
        }

        report_xml_id = 'mavaziconsignment.consignment_sales_report_pdf' if self.output_type == 'pdf' else 'mavaziconsignment.consignment_sales_report_web'
        return self.env.ref(report_xml_id).report_action(self, data=report_data)

class ConsignmentSalesReportLineTemp(models.TransientModel):
    _name = 'consignment.sales.report.line.temp'
    _description = 'Temporary Lines for Excel Export'

    vendor_name = fields.Char('Vendor')
    item_number = fields.Char('Item Number')
    item_name = fields.Char('Item Name')
    qty_sold = fields.Float('Qty Sold')
    net_sales = fields.Float('Net Sales')
    vat_amount = fields.Float('VAT Amount')
    gross_amount = fields.Float('Gross Sales')