from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import uuid


class PosCNote(models.Model):
    _name = 'pos.c.note'
    _description = 'POS Store Credit (C-Note)'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ------------------------------------------------------------
    # CORE FIELDS
    # ------------------------------------------------------------

    name = fields.Char(
        string='C-Note Code',
        readonly=True,
        copy=False,
        default=lambda self: _('New')
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('used', 'Used'),
        ('expired', 'Expired')
    ], string='Status', compute='_compute_state', store=True, default='active', tracking=True)

    active = fields.Boolean(
        string="Open",
        compute="_compute_active",
        store=True,
        default=True
    )

    original_amount = fields.Monetary(
        string='Original Amount',
        required=True,
        tracking=True
    )

    remaining_amount = fields.Monetary(
        string='Remaining Amount',
        required=True,
        tracking=True
    )

    applied_amount = fields.Monetary(
        string='Applied Amount',
        compute='_compute_applied_amount',
        store=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )

    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        tracking=True
    )

    expiry_date = fields.Date(
        string='Expiry Date',
        tracking=True
    )

    # Traceability
    source_order_id = fields.Many2one(
        'pos.order',
        string='Source Refund Order',
        readonly=True
    )

    redeemed_order_ids = fields.Many2many(
        'pos.order',
        string='Redeemed in Orders',
        readonly=True
    )

    # ------------------------------------------------------------
    # COMPUTES
    # ------------------------------------------------------------

    @api.depends('original_amount', 'remaining_amount')
    def _compute_applied_amount(self):
        for rec in self:
            rec.applied_amount = rec.original_amount - rec.remaining_amount

    @api.depends('remaining_amount', 'expiry_date')
    def _compute_state(self):
        today = fields.Date.today()
        for rec in self:
            if rec.remaining_amount <= 0:
                rec.state = 'used'
            elif rec.expiry_date and rec.expiry_date < today:
                rec.state = 'expired'
            else:
                rec.state = 'active'

    @api.depends('state')
    def _compute_active(self):
        for rec in self:
            rec.active = rec.state == 'active'

    # ------------------------------------------------------------
    # CREATE OVERRIDE
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('pos.c.note')
                vals['name'] = seq or 'CN-' + uuid.uuid4().hex[:8].upper()

            if 'remaining_amount' not in vals and 'original_amount' in vals:
                vals['remaining_amount'] = vals['original_amount']

        return super().create(vals_list)

    # ------------------------------------------------------------
    # REDEEM LOGIC (USED DURING SALE)
    # ------------------------------------------------------------

    def redeem(self, amount, order_id=False):
        for rec in self:
            if rec.state != 'active':
                raise ValidationError(
                    _("C-Note %s is %s and cannot be used.") % (rec.name, rec.state)
                )

            if amount > rec.remaining_amount:
                raise ValidationError(
                    _("Insufficient balance on C-Note %s.") % rec.name
                )

            vals = {
                'remaining_amount': rec.remaining_amount - amount
            }

            if order_id:
                vals['redeemed_order_ids'] = [(4, order_id)]

            rec.write(vals)

        return True

    # ------------------------------------------------------------
    # POS RPC ENTRYPOINT
    # ------------------------------------------------------------

    @api.model
    def create_from_pos(self, vals):
        """
        POS-safe RPC for issuing store credit from refunds
        """
        cnote = self.create(vals)
        return {
            'id': cnote.id,
            'name': cnote.name,
            'remaining_amount': cnote.remaining_amount,
        }


# ------------------------------------------------------------
# HARD BACKEND SAFETY: REFUNDS MUST NOT HAVE PAYMENTS
# ------------------------------------------------------------

class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.constrains('amount_total', 'payment_ids')
    def _check_refund_has_no_payments(self):
        for order in self:
            if order.amount_total < 0 and order.payment_ids:
                raise ValidationError(
                    _("Refund orders must be issued as store credit only (C-Note).")
                )
