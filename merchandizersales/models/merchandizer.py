from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class Merchandizer(models.Model):
    _name = 'x_merchandizer.sales'
    _description = 'Merchandizer Sales Person'
    _rec_name = 'name'
    _order = 'code'
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Merchandizer code must be unique!')
    ]

    code = fields.Char(string='Merchandizer Code', required=True)
    name = fields.Char(string='Full Name', required=True)
    mobile = fields.Char(string='Mobile Number', required=True)
    active = fields.Boolean(string='Active', default=True)

    @api.constrains('mobile')
    def _check_mobile(self):
        for record in self:
            if record.mobile and not record.mobile.isdigit():
                raise ValidationError(_('Mobile number should contain only digits.'))


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        """ Add the merchandizer model to the list of models loaded into the POS cache """
        result = super()._pos_ui_models_to_load()
        if 'x_merchandizer.sales' not in result:
            result.append('x_merchandizer.sales')
        return result

    def _loader_params_x_merchandizer_sales(self):
        """ Define which fields are sent to the browser for the merchandizer model """
        return {
            'search_params': {
                'domain': [('active', '=', True)],
                'fields': ['id', 'name', 'code'],  # Only include necessary fields
            },
        }