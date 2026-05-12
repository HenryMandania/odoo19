# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class Merchandizer(models.Model):
    _name = 'x_merchandizer.sales'
    _description = 'Merchandizer Sales Person'
    _rec_name = 'name'
    _order = 'code'
    
    # Reverting to the stable Odoo 19 tuple syntax to resolve the TypeError
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Merchandizer code must be unique!')
    ]

    code = fields.Char(string='Merchandizer Code', required=True)
    name = fields.Char(string='Full Name', required=True)
    mobile = fields.Char(string='Mobile Number', required=True)
    active = fields.Boolean(string='Active', default=True)

    @api.constrains('mobile')
    def _check_mobile(self):
        """Ensures mobile numbers remain numeric for integration reliability."""
        for record in self:
            if record.mobile and not record.mobile.isdigit():
                raise ValidationError(_('Mobile number should contain only digits.'))


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        """Registers the merchandizer model in the POS cache list."""
        result = super()._pos_ui_models_to_load()
        if 'x_merchandizer.sales' not in result:
            result.append('x_merchandizer.sales')
        return result

    def _loader_params_x_merchandizer_sales(self):
        """Defines the specific dataset to be loaded into the browser."""
        return {
            'search_params': {
                'domain': [('active', '=', True)],
                'fields': ['id', 'name', 'code'],
            },
        }