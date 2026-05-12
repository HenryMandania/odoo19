# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    merchandizer_id = fields.Many2one(
        'x_merchandizer.sales',
        string='Merchandizer',
        help="Sales staff responsible for this order"
    )

    @api.model
    def _order_fields(self, ui_order):
        """Map the merchandizer_id from the UI payload directly to the create dictionary."""
        vals = super(PosOrder, self)._order_fields(ui_order)
        if ui_order.get('merchandizer_id'):
            vals['merchandizer_id'] = ui_order['merchandizer_id']
        return vals

    def _pos_ui_order_fields(self):
        """Whitelist field so the POS UI knows it should be sent back to the server."""
        fields = super()._pos_ui_order_fields()
        if 'merchandizer_id' not in fields:
            fields.append('merchandizer_id')
        return fields

    def _process_order(self, order, existing_order):
        """Main entry point for syncing orders in Odoo 19."""
        _logger.info("📥 [PROCESS ORDER] Syncing order %s with Merchandizer: %s", 
                     order.get('name'), order.get('merchandizer_id'))
        
        pos_order_id = super(PosOrder, self)._process_order(order, existing_order)
        
        if order.get('merchandizer_id'):
            pos_order = self.browse(pos_order_id)
            pos_order.lines.write({'merchandizer_id': int(order['merchandizer_id'])})
            
        return pos_order_id


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    merchandizer_id = fields.Many2one(
        'x_merchandizer.sales',
        string='Merchandizer'
    )

    def _pos_ui_order_line_fields(self):
        """Ensure the line-level field is available for sync."""
        fields = super()._pos_ui_order_line_fields()
        if 'merchandizer_id' not in fields:
            fields.append('merchandizer_id')
        return fields

    @api.model
    def _order_line_fields(self, line, session_id=None):
        """Map UI line JSON to database fields."""
        res = super(PosOrderLine, self)._order_line_fields(line, session_id)
        line_data = line[2] if isinstance(line, (list, tuple)) and len(line) > 2 else {}
        m_id = line_data.get('merchandizer_id')
        
        if m_id:
            res['merchandizer_id'] = int(m_id)
        return res