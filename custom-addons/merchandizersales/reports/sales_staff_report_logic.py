from odoo import models, api
from odoo.exceptions import MissingError

class MerchandizerSalesReport(models.AbstractModel):
    _name = 'report.merchandizersales.report_sales_staff_template'
    _description = 'Merchandizer Sales Report Logic'

    @api.model
    def _get_report_values(self, docids, data=None):
        # Force Odoo to clear its cache to see the latest POS transactions
        self.env['pos.order.line'].invalidate_recordset()
        
        form = data.get('form', {}) if data else {}
        
        # --- CRASH-PROOF ID VALIDATION (Updated for x_merchandizer.sales) ---
        # browse().exists() filters out IDs (like 36) that no longer exist in the DB
        staff_ids_raw = form.get('staff_ids', [])
        product_ids_raw = form.get('product_ids', [])
        
        # We target your custom model specifically to fix the "Administrator" name issue
        staff_records = self.env['x_merchandizer.sales'].sudo().browse(staff_ids_raw).exists()
        product_records = self.env['product.product'].sudo().browse(product_ids_raw).exists()

        # Safely get names for the header - this fixes the red box in your screenshot
        staff_names = ", ".join(staff_records.mapped('name')) if staff_records else "All Merchandizers"
        product_names = ", ".join(product_records.mapped('name')) if product_records else "All Products"
        # -------------------------------------------------------------------

        domain = [
            ('order_id.date_order', '>=', form.get('date_from')),
            ('order_id.date_order', '<=', form.get('date_to')),
            ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
            ('merchandizer_id', '!=', False), 
        ]

        # Apply filters only if valid records exist
        if staff_records:
            domain.append(('merchandizer_id', 'in', staff_records.ids))
        if product_records:
            domain.append(('product_id', 'in', product_records.ids))

        # Fetch lines and double-check merchandizer existence
        lines = self.env['pos.order.line'].sudo().search(domain).filtered(lambda l: l.merchandizer_id.exists())
        
        grouped_data = {}

        for line in lines:
            m_id = line.merchandizer_id.id
            if m_id not in grouped_data:
                grouped_data[m_id] = {
                    'code': line.merchandizer_id.code or 'N/A',
                    'name': line.merchandizer_id.name,
                    'net': 0.0, 
                    'tax': 0.0, 
                    'gross': 0.0,
                    'products': {} 
                }
            
            # Financial Calculations
            grouped_data[m_id]['net'] += line.price_subtotal
            grouped_data[m_id]['gross'] += line.price_subtotal_incl
            grouped_data[m_id]['tax'] += (line.price_subtotal_incl - line.price_subtotal)
            
            # Products (Itemized)
            p_id = line.product_id.id
            if p_id not in grouped_data[m_id]['products']:
                grouped_data[m_id]['products'][p_id] = {
                    'name': line.product_id.name,
                    'ref': line.product_id.default_code or '',
                    'qty': 0.0
                }
            grouped_data[m_id]['products'][p_id]['qty'] += line.qty

        # Final Formatting and Grand Total Calculation
        final_lines = []
        total_qty_sum = 0.0
        
        for staff_id, values in grouped_data.items():
            product_list = list(values['products'].values())
            # Sum quantities from the processed lines
            total_qty_sum += sum(p['qty'] for p in product_list)
            
            values['products'] = product_list
            final_lines.append(values)

        return {
            'doc_ids': docids,
            'data': form,
            'lines': final_lines,
            'res_company': self.env.company,
            'filters': {
                'staff': staff_names,
                'products': product_names
            },
            'totals': {
                'net': sum(x['net'] for x in final_lines), 
                'tax': sum(x['tax'] for x in final_lines), 
                'gross': sum(x['gross'] for x in final_lines),
                'qty': total_qty_sum
            },
        }