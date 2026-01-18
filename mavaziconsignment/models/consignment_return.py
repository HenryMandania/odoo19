# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ConsignmentReturn(models.Model):
    _name = 'consignment.return'
    _description = 'Consignment Return'
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _('New')
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='Status', default='draft', tracking=True)

    date = fields.Date(
        string='Return Date',
        default=fields.Date.context_today,
        required=True
    )

    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        domain="[('supplier_rank', '>', 0)]"
    )

    purchase_id = fields.Many2one(
        'purchase.order',
        string='Related Purchase Order',
        domain="[('partner_id', '=', vendor_id)]"
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    line_ids = fields.One2many(
        'consignment.return.line',
        'return_id',
        string='Returned Items'
    )

    total_return_value = fields.Float(
        string='Total Return Value',
        compute='_compute_total_return_value',
        store=True
    )

    note = fields.Text(string='Reason / Notes')

    @api.depends('line_ids.price_subtotal')
    def _compute_total_return_value(self):
        for rec in self:
            rec.total_return_value = sum(rec.line_ids.mapped('price_subtotal'))

    @api.onchange('purchase_id')
    def _onchange_purchase_id(self):
        if self.purchase_id:
            self.vendor_id = self.purchase_id.partner_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('consignment.return') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                raise ValidationError(_('You must add at least one product.'))
            rec.state = 'confirmed'

    def print_return(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Printing'),
                'message': _('Preparing the return document...'),
                'sticky': False,
            }
        }


class ConsignmentReturnLine(models.Model):
    _name = 'consignment.return.line'
    _description = 'Consignment Return Line'

    return_id = fields.Many2one(
        'consignment.return',
        string='Return Reference',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
    'product.product',
    string='Product',
    required=True,
    domain="[('product_tmpl_id.x_is_consignment','=',True)]"
)


    quantity = fields.Float(
        string='Quantity',
        default=1.0
    )

    price_unit = fields.Float(
        string='Unit Price',
        compute='_compute_price_unit',
        store=True,
        readonly=False
    )

    price_subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_price_subtotal',
        store=True
    )

    remaining_qty = fields.Float(
        string='Remaining Qty',
        compute='_compute_remaining_qty',
        help="Remaining returnable quantity for this product on the selected PO"
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='return_id.currency_id',
        store=True
    )

    @api.depends('product_id')
    def _compute_price_unit(self):
        for line in self:
            line.price_unit = line.product_id.standard_price if line.product_id else 0.0

    @api.depends('quantity', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit

    @api.depends('product_id', 'return_id.purchase_id')
    def _compute_remaining_qty(self):
        for line in self:
            po_lines = line.return_id.purchase_id.order_line.filtered(lambda l: l.product_id == line.product_id)
            if po_lines:
                po_qty = po_lines[0].product_qty
                previous_returns = self.search([
                    ('return_id.purchase_id', '=', line.return_id.purchase_id.id),
                    ('product_id', '=', line.product_id.id),
                    ('id', '!=', line.id)
                ])
                returned_qty = sum(previous_returns.mapped('quantity'))
                line.remaining_qty = max(po_qty - returned_qty, 0.0)
            else:
                line.remaining_qty = 0.0

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Return quantity must be greater than zero.'))
            if line.quantity > line.remaining_qty:
                raise ValidationError(_('Cannot return more than remaining quantity (%s) for %s') %
                                      (line.remaining_qty, line.product_id.display_name))

    @api.onchange('return_id.state')
    def _onchange_confirmed(self):
        if self.return_id.state == 'confirmed':
            return {
                'warning': {
                    'title': _('Action Forbidden'),
                    'message': _('Cannot edit lines on a confirmed return.')
                }
            }
