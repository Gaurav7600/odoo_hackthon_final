# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PlmEcoProductChange(models.Model):
    """Proposed field-level change on a PLM Product inside an ECO."""
    _name = 'plm.eco.product.change'
    _description = 'ECO Product Field Change'
    _order = 'eco_id, id'

    eco_id = fields.Many2one(
        'plm.eco', required=True, ondelete='cascade', index=True,
    )
    field_name = fields.Selection([
        ('name',        'Product Name'),
        ('sale_price',  'Sale Price'),
        ('cost_price',  'Cost Price'),
        ('description', 'Description'),
    ], string='Field', required=True)

    field_label = fields.Char(
        string='Field Label',
        compute='_compute_label',
        store=True,
    )
    old_value = fields.Char(string='Current Value', readonly=True)
    new_value = fields.Char(string='Proposed Value')

    change_status = fields.Selection([
        ('added',     'Added'),
        ('removed',   'Removed'),
        ('modified',  'Modified'),
        ('unchanged', 'Unchanged'),
    ], compute='_compute_status', store=True, string='Change Status')

    @api.depends('field_name')
    def _compute_label(self):
        labels = {
            'name':        'Product Name',
            'sale_price':  'Sale Price',
            'cost_price':  'Cost Price',
            'description': 'Description',
        }
        for r in self:
            r.field_label = labels.get(r.field_name, r.field_name)

    @api.depends('old_value', 'new_value')
    def _compute_status(self):
        for r in self:
            if not r.old_value and r.new_value:
                r.change_status = 'added'
            elif r.old_value and not r.new_value:
                r.change_status = 'removed'
            elif (r.old_value or '') != (r.new_value or ''):
                r.change_status = 'modified'
            else:
                r.change_status = 'unchanged'


class PlmEcoBomChange(models.Model):
    """Proposed component-level change on a PLM BoM inside an ECO."""
    _name = 'plm.eco.bom.change'
    _description = 'ECO BoM Component Change'
    _order = 'eco_id, change_type, id'

    eco_id = fields.Many2one(
        'plm.eco', required=True, ondelete='cascade', index=True,
    )
    component_id = fields.Many2one(
        'plm.product',
        string='Component',
        required=True,
        domain="[('status', '=', 'active')]",
        ondelete='restrict',
    )
    component_name = fields.Char(
        related='component_id.name',
        string='Component Name',
        store=True,
        readonly=True,
    )
    change_type = fields.Selection([
        ('added',     'Added'),
        ('removed',   'Removed'),
        ('modified',  'Modified'),
        ('unchanged', 'Unchanged'),
    ], string='Change Type', required=True, default='unchanged')

    old_qty = fields.Float(
        string='Current Qty',
        digits=(12, 4),
        default=0.0,
    )
    new_qty = fields.Float(
        string='Proposed Qty',
        digits=(12, 4),
        default=0.0,
    )
    product_uom = fields.Char(
        string='Unit of Mesure',
        compute='_compute_product_uom',
        store=True,
    )
    qty_diff = fields.Float(
        string='Difference',
        compute='_compute_diff',
        store=True,
        digits=(12, 4),
    )

    @api.depends('component_id')
    def _compute_product_uom(self):
        for r in self:
            r.product_uom = r.component_id.product_uom if r.component_id else ''

    @api.depends('old_qty', 'new_qty')
    def _compute_diff(self):
        for r in self:
            r.qty_diff = r.new_qty - r.old_qty

    @api.onchange('new_qty', 'old_qty')
    def _onchange_qty(self):
        if self.old_qty == 0 and self.new_qty > 0:
            self.change_type = 'added'
        elif self.old_qty > 0 and self.new_qty == 0:
            self.change_type = 'removed'
        elif self.old_qty != self.new_qty:
            self.change_type = 'modified'
        else:
            self.change_type = 'unchanged'

    @api.constrains('new_qty', 'change_type')
    def _check_qty(self):
        for r in self:
            if r.change_type in ('added', 'modified') and r.new_qty <= 0:
                raise ValidationError(f"Proposed quantity must be > 0 for component {r.component_id.name}")


class PlmEcoOperationChange(models.Model):
    _name = 'plm.eco.operation.change'
    _description = 'ECO Operation Change'
    _order = 'eco_id, id'

    eco_id = fields.Many2one(
        'plm.eco', required=True, ondelete='cascade', index=True,
    )
    operation_name = fields.Char(string='Operation Name', required=True)
    work_center = fields.Char(
        string='Work Center',
        help='e.g. Assembly Line, Paint Floor, Packaging Line',
    )
    change_type = fields.Selection([
        ('added',     'Added'),
        ('removed',   'Removed'),
        ('modified',  'Modified'),
        ('unchanged', 'Unchanged'),
    ], string='Change Type', required=True, default='unchanged')

    old_duration = fields.Float(
        string='Current Duration (min)',
        digits=(8, 2),
        default=0.0,
    )
    new_duration = fields.Float(
        string='Proposed Duration (min)',
        digits=(8, 2),
        default=0.0,
    )
    duration_diff = fields.Float(
        string='Difference (min)',
        compute='_compute_diff',
        store=True,
        digits=(8, 2),
    )

    @api.depends('old_duration', 'new_duration')
    def _compute_diff(self):
        for r in self:
            r.duration_diff = r.new_duration - r.old_duration

    @api.onchange('new_duration', 'old_duration')
    def _onchange_duration(self):
        if self.old_duration == 0 and self.new_duration > 0:
            self.change_type = 'added'
        elif self.old_duration > 0 and self.new_duration == 0:
            self.change_type = 'removed'
        elif self.old_duration != self.new_duration:
            self.change_type = 'modified'
        else:
            self.change_type = 'unchanged'

    @api.constrains('new_duration', 'change_type')
    def _check_duration(self):
        for r in self:
            if r.change_type in ('added', 'modified') and r.new_duration < 0:
                raise ValidationError(f"Duration cannot be negative for operation {r.operation_name}")
