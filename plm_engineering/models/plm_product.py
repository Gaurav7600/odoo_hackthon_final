# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PlmProduct(models.Model):
    _name = 'plm.product'
    _description = 'PLM Product Master'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name, version_number desc'
    _rec_name = 'display_name_full'

    name = fields.Char(
        string='Product Name',
        required=True,
        tracking=True,
        help='The name of this product.',
    )
    internal_ref = fields.Char(
        string='Internal Reference',
        tracking=True,
        help='Unique internal code or SKU for this product.',
    )
    category = fields.Selection([
        ('raw_material', 'Raw Material'),
        ('semi_finished', 'Semi-Finished'),
        ('finished_good', 'Finished Good'),
        ('consumable', 'Consumable'),
        ('service', 'Service'),
    ], string='Category', default='finished_good', tracking=True)

    description = fields.Text(string='Product Description', tracking=True)

    sale_price = fields.Float(
        string='Sale Price',
        digits=(16, 4),
        default=0.0,
        tracking=True,
        help='The customer-facing sale price of this product.',
    )
    cost_price = fields.Float(
        string='Cost Price',
        digits=(16, 4),
        default=0.0,
        tracking=True,
        help='The internal manufacturing or procurement cost.',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    product_uom = fields.Many2one(
        'plm.product.uom',
        string='Unit of Measure',
    )

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'plm_product_attachment_rel',
        'product_id', 'attachment_id',
        string='Attachments ',
        help='Technical drawings, specifications, certificates, etc.',
    )
    attachment_count = fields.Integer(
        compute='_compute_attachment_count',
        string='Attachments',
    )

    version = fields.Char(
        string='Version',
        default='v1',
        required=True,
        copy=False,
        tracking=True,
        help='PLM version string e.g. v1, v2, v3.',
    )
    version_number = fields.Integer(
        string='Version Number',
        default=1,
        copy=False,
        readonly=True,
        help='Numeric version for sorting.',
    )
    parent_product_id = fields.Many2one(
        'plm.product',
        string='Previous Version',
        copy=False,
        readonly=True,
        ondelete='set null',
        help='The product version this was created from.',
    )
    child_version_ids = fields.One2many(
        'plm.product',
        'parent_product_id',
        string='Subsequent Versions',
        readonly=True,
    )
    version_count = fields.Integer(
        compute='_compute_version_count',
        string='Sub-Versions',
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
        help='Active: usable in BoMs and ECOs.\n'
            'Archived: read-only, retained for traceability only.',
    )

    display_name_full = fields.Char(
        compute='_compute_display_name_full',
        store=True,
        string='Full Name',
    )
    bom_count = fields.Integer(
        compute='_compute_bom_count',
        string='Bills of Materials',
    )
    eco_count = fields.Integer(
        compute='_compute_eco_count',
        string='ECOs',
    )

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Important'),
        ('2', 'Very Urgent'),
        ('3', 'Critical'),
    ], string='Priority', default='0')

    @api.depends('name', 'version', 'status')
    def _compute_display_name_full(self):
        for p in self:
            status_tag = ' [Archived]' if p.status == 'archived' else ''
            p.display_name_full = f"{p.name or ''} ({p.version or 'v1'}){status_tag}"

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for p in self:
            p.attachment_count = len(p.attachment_ids)

    @api.depends('child_version_ids')
    def _compute_version_count(self):
        for p in self:
            p.version_count = len(p.child_version_ids)

    def _compute_bom_count(self):
        for p in self:
            p.bom_count = self.env['plm.bom'].search_count([('product_id', '=', p.id)])

    def _compute_eco_count(self):
        for p in self:
            p.eco_count = self.env['plm.eco'].search_count([('product_id', '=', p.id)])

    @api.constrains('name', 'version')
    def _check_unique_version(self):
        for rec in self:
            domain = [
                ('name', '=', rec.name),
                ('version', '=', rec.version),
                ('id', '!=', rec.id),
            ]
            if self.search(domain, limit=1):
                raise ValidationError(f"Product {rec.name} already has a version {rec.version} Each product version must be unique.")

    def write(self, vals):
        protected = {'name', 'sale_price', 'cost_price', 'product_uom', 'category',
                    'internal_ref', 'description', 'attachment_ids'}
        for rec in self:
            if rec.status == 'archived' and any(f in vals for f in protected):
                raise UserError(f"Product {rec.name} {rec.version} is Archived and cannot be edited directly.\n\n"
                    "Create an Engineering Change Order (ECO) to propose changes.")
        return super().write(vals)

    def action_view_boms(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bills of Materials — %s (%s)') % (self.name, self.version),
            'res_model': 'plm.bom',
            'view_mode': 'list,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id},
        }

    def action_view_ecos(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('ECOs — %s (%s)') % (self.name, self.version),
            'res_model': 'plm.eco',
            'view_mode': 'list,kanban,form',
            'domain': [('product_id', '=', self.id)],
        }

    def action_view_version_history(self):
        self.ensure_one()
        root = self
        while root.parent_product_id:
            root = root.parent_product_id

        all_ids = self._get_all_version_ids(root)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Version History — %s') % root.name,
            'res_model': 'plm.product',
            'view_mode': 'list,form',
            'domain': [('id', 'in', all_ids)],
        }

    def _get_all_version_ids(self, root):
        ids = [root.id]
        for child in root.child_version_ids:
            ids += self._get_all_version_ids(child)
        return ids

    def action_create_eco(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('New ECO for %s') % self.name,
            'res_model': 'plm.eco',
            'view_mode': 'form',
            'context': {
                'default_product_id': self.id,
                'default_eco_type': 'product',
            },
        }
