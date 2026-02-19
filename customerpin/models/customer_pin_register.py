from odoo import models, fields

class CustomerPinRegister(models.Model):
    _name = "customer.pin.register"
    _description = "Customer PIN Register"
    _rec_name = "name"

    name = fields.Char(string="Customer Name", required=True)
    mobile = fields.Char(string="Mobile Number", required=True)
    kra_pin = fields.Char(string="KRA PIN", required=True)

    _sql_constraints = [
        ("unique_mobile", "unique(mobile)", "Mobile number must be unique"),
        ("unique_kra_pin", "unique(kra_pin)", "KRA PIN must be unique"),
    ]

