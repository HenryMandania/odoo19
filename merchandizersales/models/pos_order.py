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

    def _pos_ui_order_fields(self):
        """Whitelist extra field for PoS sync."""
        fields = super()._pos_ui_order_fields()
        if 'merchandizer_id' not in fields:
            fields.append('merchandizer_id')
        _logger.info("⭐ [WHITELIST] Added merchandizer_id to order fields")
        return fields

    def _process_order(self, order, existing_order):
        """Main entry point in Odoo 19 for processing synced orders."""
        _logger.info("📥 [PROCESS ORDER] Incoming order: %s | UUID: %s | Merchandizer: %s",
                     order.get('name'), order.get('uuid'), order.get('merchandizer_id'))

        # super() returns an integer ID in Odoo 19
        pos_order_id = super()._process_order(order, existing_order)
        pos_order = self.browse(pos_order_id)

        # Persist merchandizer on order header
        if order.get('merchandizer_id'):
            try:
                merch_id = int(order['merchandizer_id'])
                pos_order.write({'merchandizer_id': merch_id})
                _logger.info("✅ [DB WRITE] Order %s updated with merchandizer_id %s",
                             pos_order.id, merch_id)

                # Update all lines with same merchandizer
                for line in pos_order.lines:
                    line.write({'merchandizer_id': merch_id})
                    _logger.info("✅ [LINE DB WRITE] Line %s updated with merchandizer_id %s",
                                 line.id, merch_id)
            except Exception as e:
                _logger.error("❌ [DB WRITE] Failed to persist merchandizer_id: %s", e)
        else:
            _logger.info("⚠️ [PROCESS ORDER] No merchandizer_id in payload")

        # Summary log of final DB values
        _logger.info("📊 [FINAL ORDER] ID: %s | Name: %s | Merchandizer: %s",
                     pos_order.id, pos_order.name,
                     pos_order.merchandizer_id.display_name if pos_order.merchandizer_id else None)

        return pos_order_id


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    merchandizer_id = fields.Many2one(
        'x_merchandizer.sales',
        string='Merchandizer',
        help="Sales staff responsible for this order line"
    )

    def _pos_ui_order_line_fields(self):
        """Whitelist extra field for PoS sync."""
        fields = super()._pos_ui_order_line_fields()
        if 'merchandizer_id' not in fields:
            fields.append('merchandizer_id')
        _logger.info("⭐ [WHITELIST] Added merchandizer_id to order line fields")
        return fields

    @api.model
    def _order_line_fields(self, line, session_id=None):
        """Map UI JSON to DB fields for order line."""
        res = super(PosOrderLine, self)._order_line_fields(line, session_id)
        line_data = line[2] if isinstance(line, (list, tuple)) and len(line) > 2 else {}
        m_id = line_data.get('merchandizer_id')
        _logger.info("📝 [LINE PROCESS] Product: %s | Qty: %s | Merchandizer: %s",
                     line_data.get('product_id'), line_data.get('qty'), m_id)
        if m_id:
            try:
                res['merchandizer_id'] = int(m_id)
                _logger.info("✅ [LINE MAPPED] Product: %s | Merchandizer: %s",
                             line_data.get('product_id'), m_id)
            except (ValueError, TypeError) as e:
                _logger.error("❌ [LINE MAPPED] Invalid merchandizer_id format: %s", e)
        else:
            _logger.info("⚠️ [LINE PROCESS] No merchandizer_id in line data")
        return res
