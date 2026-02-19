from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    customer_pin_id = fields.Many2one(
        'customer.pin.register',
        string='Customer PIN'
    )
    kra_qrcode = fields.Char(string='KRA QR Code')

    def _pos_ui_order_fields(self):
        """Whitelist extra fields for PoS sync."""
        fields = super()._pos_ui_order_fields()
        for f in ['customer_pin_id', 'kra_qrcode']:
            if f not in fields:
                fields.append(f)
        _logger.info("⭐ [WHITELIST] Added customer_pin_id & kra_qrcode to order fields")
        return fields

    def _process_order(self, order, existing_order):
        """Persist custom fields when processing synced orders."""
        pos_order_id = super()._process_order(order, existing_order)
        pos_order = self.browse(pos_order_id)

        if order.get('customer_pin_id'):
            try:
                pos_order.write({
                    'customer_pin_id': int(order['customer_pin_id']),
                    'kra_qrcode': order.get('kra_qrcode'),
                })
                _logger.info("✅ [DB WRITE] Order %s updated with customer_pin_id %s",
                             pos_order.id, order['customer_pin_id'])
            except Exception as e:
                _logger.error("❌ Failed to persist customer_pin_id: %s", e)
        else:
            _logger.info("⚠️ No customer_pin_id in payload")

        return pos_order_id
