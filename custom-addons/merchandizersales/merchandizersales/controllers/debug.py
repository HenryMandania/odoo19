# controllers/debug.py

from odoo import http
import logging

_logger = logging.getLogger(__name__)

class MerchandizerDebugController(http.Controller):
    
    @http.route('/merchandizer/test', type='http', auth='none')
    def test_module(self):
        """Simple test to see if module is loaded"""
        _logger.info("✅ Merchandizer debug endpoint called")
        return "Merchandizer module is loaded!"