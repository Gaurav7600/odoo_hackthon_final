# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PlmBom(models.Model):
    """
    Custom PLM Bill of Materials.
    Represents the manufacturing structure of a specific product version.
    All changes must go through a BoM ECO.
    """
    _name = 'plm.bom'
    _description = 'PLM Bill of Materials'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'product_id, version_number desc'
    _rec_name = 'display_name_full'

    name = fields.Char(
        string='BoM Reference',
        required=True,
        tracking=True,
        help='Descriptive name for this Bill of Materials.',
    )
    product_id = fields.Many2one(
        'plm.product',
        string='Product',
        required=True,
        ondelete='restrict',
        tracking=True,
        domain="[('status', '=', 'active')]",
        help='The product this BoM produces. Only active products are selectable.',
    )
    product_qty = fields.Float(
        string='Produces Quantity',
        default=1.0,
        digits=(12, 4),
        required=True,
        help='The output quantity this BoM produces.',
    )
    product_uom = fields.Char(
        string='Unit',
        related='product_id.uom',
        readonly=True,
    )
    notes = fields.Text(string='Notes / Instructions')

    version = fields.Char(
        string='BoM Version',
        default='v1',
        required=True,
        copy=False,
        tracking=True,
    )
    version_number = fields.Integer(
        string='Version Number',
        default=1,
        copy=False,
        readonly=True,
    )
    created_by_eco_id = fields.Many2one(
        'plm.eco',
        string='Created by ECO',
        copy=False,
        readonly=True,
        ondelete='set null',
    )

    status = fields.Selection([
        ('active', 'Active'),
        ('archived', 'Archived'),
    ], string='PLM Status',
        default='active',
        required=True,
        copy=False,
        tracking=True,
        help='Active: usable in Manufacturing Orders.\n'
            'Archived: read-only, retained for audit.',
    )

    line_ids = fields.One2many(
        'plm.bom.line',
        'bom_id',
        string='Components',
        copy=True,
    )
    operation_ids = fields.One2many(
        'plm.bom.operation',
        'bom_id',
        string='Operations',
        copy=True,
    )

    display_name_full = fields.Char(
        compute='_compute_display_name_full',
        store=True,
        string='Full Name',
    )
    component_count = fields.Integer(
        compute='_compute_counts',
        string='Components',
    )
    operation_count = fields.Integer(
        compute='_compute_counts',
        string='Operations',
    )
    eco_count = fields.Integer(
        compute='_compute_eco_count',
        string='ECOs',
    )
    total_component_cost = fields.Float(
        compute='_compute_total_cost',
        string='Est. Component Cost',
        digits=(16, 4),
        store=False,
    )


    @api.depends('name', 'product_id', 'version', 'status')
    def _compute_display_name_full(self):
        for b in self:
            pname = b.product_id.name if b.product_id else 'N/A'
            status_tag = ' [Archived]' if b.status == 'archived' else ''
            b.display_name_full = f"{pname} — {b.name} ({b.version}){status_tag}"

    @api.depends('line_ids', 'operation_ids')
    def _compute_counts(self):
        for b in self:
            b.component_count = len(b.line_ids)
            b.operation_count = len(b.operation_ids)

    def _compute_eco_count(self):
        for b in self:
            b.eco_count = self.env['plm.eco'].search_count([('bom_id', '=', b.id)])

    @api.depends('line_ids.subtotal_cost')
    def _compute_total_cost(self):
        for b in self:
            b.total_component_cost = sum(b.line_ids.mapped('subtotal_cost'))

    @api.constrains('product_id', 'version')
    def _check_unique_version(self):
        for rec in self:
            domain = [
                ('product_id', '=', rec.product_id.id),
                ('version', '=', rec.version),
                ('id', '!=', rec.id),
            ]
            if self.search(domain, limit=1):
                raise ValidationError(
                    _("Product '%s' already has a BoM with version '%s'.")
                    % (rec.product_id.name, rec.version)
                )

    def write(self, vals):
        protected = {'line_ids', 'operation_ids', 'product_id', 'product_qty', 'name'}
        for rec in self:
            if rec.status == 'archived' and any(f in vals for f in protected):
                raise UserError(
                    _("BoM '%s' is Archived and cannot be edited directly.\n\n"
                    "Create a BoM Engineering Change Order (ECO) to propose changes.")
                    % rec.display_name_full
                )
        return super().write(vals)

    def action_view_ecos(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('ECO History — %s') % self.display_name_full,
            'res_model': 'plm.eco',
            'view_mode': 'list,form',
            'domain': [('bom_id', '=', self.id)],
        }

    def action_create_eco(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('New BoM ECO'),
            'res_model': 'plm.eco',
            'view_mode': 'form',
            'context': {
                'default_product_id': self.product_id.id,
                'default_bom_id': self.id,
                'default_eco_type': 'bom',
            },
        }

    def action_view_components(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Components — %s') % self.display_name_full,
            'res_model': 'plm.bom.line',
            'view_mode': 'list',
            'views': [(self.env.ref('plm_engineering.view_plm_bom_line_list').id, 'list')],
            'domain': [('bom_id', '=', self.id)],
            'context': {'default_bom_id': self.id},
        }

    def action_view_operations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Operations — %s') % self.display_name_full,
            'res_model': 'plm.bom.operation',
            'view_mode': 'list',
            'views': [(self.env.ref('plm_engineering.view_plm_bom_operation_list').id, 'list')],
            'domain': [('bom_id', '=', self.id)],
            'context': {'default_bom_id': self.id},
        }


class PlmBomLine(models.Model):
    """
    Custom Bill of Materials Component Line.
    Each line represents one component and its quantity.
    """
    _name = 'plm.bom.line'
    _description = 'PLM BoM Component Line'
    _order = 'sequence, id'

    bom_id = fields.Many2one(
        'plm.bom',
        string='Bill of Materials',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)

    component_id = fields.Many2one(
        'plm.product',
        string='Component',
        required=True,
        ondelete='restrict',
        domain="[('status', '=', 'active')]",
        help='Component product. Only active products are selectable.',
    )
    component_name = fields.Char(
        related='component_id.name',
        string='Component Name',
        readonly=True,
        store=True,
    )
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        digits=(12, 4),
        required=True,
    )
    uom = fields.Char(
        string='Unit',
        related='component_id.uom',
        readonly=True,
    )
    cost_price = fields.Float(
        related='component_id.cost_price',
        string='Unit Cost',
        readonly=True,
        digits=(16, 4),
    )
    subtotal_cost = fields.Float(
        compute='_compute_subtotal',
        string='Subtotal Cost',
        digits=(16, 4),
        store=True,
    )
    note = fields.Char(string='Note')

    @api.depends('quantity', 'cost_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal_cost = line.quantity * line.cost_price

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(
                    _("Quantity for component '%s' must be greater than zero.")
                    % line.component_id.name
                )


class PlmBomOperation(models.Model):
    """
    Custom Bill of Materials Operation / Routing line.
    Defines the work steps required to manufacture the product.
    """
    _name = 'plm.bom.operation'
    _description = 'PLM BoM Operation'
    _order = 'sequence, id'

    bom_id = fields.Many2one(
        'plm.bom',
        string='Bill of Materials',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Operation Name', required=True)
    work_center = fields.Char(
        string='Work Center',
        required=True,
        help='e.g. Assembly Line, Paint Floor, Packaging Line',
    )
    duration_minutes = fields.Float(
        string='Duration (min)',
        default=0.0,
        digits=(8, 2),
        required=True,
        help='Time required for this operation in minutes.',
    )
    note = fields.Char(string='Note')

    @api.constrains('duration_minutes')
    def _check_duration(self):
        for op in self:
            if op.duration_minutes < 0:
                raise ValidationError(
                    _("Duration for operation '%s' cannot be negative.") % op.name
                )
