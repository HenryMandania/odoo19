# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ConsignmentSalesReportWizard(models.TransientModel):
    _name = 'consignment.sales.report.wizard'
    _description = 'Wizard for Consignment Sales Report'

    date_from = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    vendor_id = fields.Many2one('res.partner', string='Vendor', domain="[('supplier_rank','>',0)]")
    
    # Updated to use x_is_consignment for the selection domain
    product_id = fields.Many2one('product.product', string='Product', domain="[('x_is_consignment','=',True)]")
    
    output_type = fields.Selection([
        ('pdf', 'PDF Report'),
        ('web', 'Web View (HTML)')
    ], string='Output Format', default='pdf', required=True)

    def action_print_report(self):
        """Strictly filters by the custom 'x_is_consignment' field"""
        # We define the domain to strictly require x_is_consignment = True
        domain = [
            ('order_id.date_order', '>=', self.date_from),
            ('order_id.date_order', '<=', self.date_to),
            ('product_id.x_is_consignment', '=', True), # Updated field name
            ('order_id.state', 'in', ['paid', 'done', 'invoiced'])
        ]
        
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        
        # If a vendor is selected, we filter the lines to only those belonging to that vendor
        if self.vendor_id:
            domain.append(('product_id.seller_ids.partner_id', '=', self.vendor_id.id))

        # We execute the search on pos.order.line
        lines = self.env['pos.order.line'].search(domain)
        
        data_lines = []
        totals = {'qty_sold': 0, 'net_sales': 0.0, 'vat_amount': 0.0, 'gross_amount': 0.0}

        for line in lines:
            net = line.price_subtotal
            gross = line.price_subtotal_incl
            vat = gross - net
            
            # Fetch the first vendor from the product's Purchase tab
            vendor = line.product_id.seller_ids[0].partner_id if line.product_id.seller_ids else False
            
            data_lines.append({
                'vendor_name': vendor.name if vendor else 'No Vendor',
                'item_number': line.product_id.default_code or '',
                'item_name': line.product_id.name,
                'qty_sold': line.qty,
                'net_sales': net,
                'vat_amount': vat,
                'gross_amount': gross,
            })
            totals['qty_sold'] += line.qty
            totals['net_sales'] += net
            totals['vat_amount'] += vat
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