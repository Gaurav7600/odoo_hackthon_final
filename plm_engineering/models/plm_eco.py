# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PlmEco(models.Model):
    """
    Engineering Change Order (ECO) — the central object for managing
    version-controlled changes to PLM Products and Bills of Materials.

    Lifecycle: Draft → In Review → Approval → Done
    Changes are stored separately and never touch master data until applied.
    """
    _name = 'plm.eco'
    _description = 'PLM Engineering Change Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'
    _rec_name = 'name'

    # ── Identity ─────────────────────────────────────────────────────
    name = fields.Char(
        string='ECO Title',
        required=True,
        tracking=True,
        help='Short descriptive title for this Engineering Change Order.',
    )
    reference = fields.Char(
        string='Reference',
        readonly=True,
        copy=False,
        default='New',
        help='Auto-generated unique reference number.',
    )
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Important'),
        ('2', 'Very Urgent'),
        ('3', 'Critical'),
    ], string='Priority', default='0', tracking=True)

    eco_type = fields.Selection([
        ('product', 'Product Change'),
        ('bom', 'BoM Change'),
    ], string='ECO Type',
        required=True,
        tracking=True,
        help='Product ECO: changes to product name, pricing, attachments.\n'
             'BoM ECO: changes to components, quantities, and operations.',
    )

    # ── Related Documents ─────────────────────────────────────────────
    product_id = fields.Many2one(
        'plm.product',
        string='Product',
        required=True,
        tracking=True,
        domain="[('status', '=', 'active')]",
        help='Target product. Only active product versions are selectable.',
    )
    bom_id = fields.Many2one(
        'plm.bom',
        string='Bill of Materials',
        tracking=True,
        domain="[('product_id', '=', product_id), ('status', '=', 'active')]",
        help='Required for BoM ECOs. Must belong to the selected product.',
    )

    # ── People & Dates ────────────────────────────────────────────────
    user_id = fields.Many2one(
        'res.users',
        string='Responsible Engineer',
        default=lambda self: self.env.user,
        tracking=True,
    )
    effective_date = fields.Date(
        string='Effective Date',
        tracking=True,
        help='The date this change is planned to go into effect.',
    )
    applied_date = fields.Datetime(
        string='Applied On',
        readonly=True,
        copy=False,
    )
    applied_by_id = fields.Many2one(
        'res.users',
        string='Applied By',
        readonly=True,
        copy=False,
    )

    # ── Stage / State ─────────────────────────────────────────────────
    stage_id = fields.Many2one(
        'plm.eco.stage',
        string='Stage',
        required=True,
        tracking=True,
        default=lambda self: self.env['plm.eco.stage']._get_start_stage(),
        group_expand='_read_group_stage_ids',
    )
    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('done', 'Ready for Next Stage'),
        ('blocked', 'Blocked'),
    ], string='Kanban State', default='normal', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
        ('done', 'Done / Applied'),
        ('cancelled', 'Cancelled'),
    ], string='Status',
        compute='_compute_state',
        store=True,
        tracking=True,
        help='Computed from the current stage and approval state.',
    )
    is_approved = fields.Boolean(
        string='Approved',
        default=False,
        copy=False,
        tracking=True,
    )

    # ── Versioning ────────────────────────────────────────────────────
    version_update = fields.Boolean(
        string='Create New Version on Apply',
        default=True,
        tracking=True,
        help='Enabled → a new version is created when this ECO is applied.\n'
             'Disabled → changes are applied to the existing version directly.',
    )
    current_version = fields.Char(
        string='Current Version',
        compute='_compute_version_info',
        store=False,
    )
    new_version_label = fields.Char(
        string='New Version (Preview)',
        compute='_compute_version_info',
        store=False,
    )

    # ── Change Lines ──────────────────────────────────────────────────
    product_change_ids = fields.One2many(
        'plm.eco.product.change',
        'eco_id',
        string='Product Field Changes',
        copy=True,
    )
    bom_change_ids = fields.One2many(
        'plm.eco.bom.change',
        'eco_id',
        string='Component Changes',
        copy=True,
    )
    operation_change_ids = fields.One2many(
        'plm.eco.operation.change',
        'eco_id',
        string='Operation Changes',
        copy=True,
    )

    # ── Approval Records ──────────────────────────────────────────────
    approval_ids = fields.One2many(
        'plm.eco.approval',
        'eco_id',
        string='Approval Records',
    )
    approval_count = fields.Integer(
        compute='_compute_approval_count',
        string='Approvals',
    )

    # ── Audit Logs ────────────────────────────────────────────────────
    audit_log_ids = fields.One2many(
        'plm.audit.log',
        'eco_id',
        string='Audit Trail',
    )
    audit_count = fields.Integer(
        compute='_compute_audit_count',
        string='Audit Events',
    )

    # ── Counts ────────────────────────────────────────────────────────
    change_count = fields.Integer(
        compute='_compute_change_count',
        string='Total Changes',
    )

    # ── Notes ─────────────────────────────────────────────────────────
    note = fields.Html(string='Internal Notes')

    # ══════════════════════════════════════════════════════════════════
    #  Compute Methods
    # ══════════════════════════════════════════════════════════════════

    @api.depends('stage_id', 'stage_id.is_final_stage',
                 'stage_id.is_start_stage', 'stage_id.is_approval_required',
                 'is_approved')
    def _compute_state(self):
        for eco in self:
            if not eco.stage_id:
                eco.state = 'draft'
            elif eco.stage_id.is_final_stage:
                eco.state = 'done'
            elif eco.stage_id.is_start_stage:
                eco.state = 'draft'
            elif eco.stage_id.is_approval_required and eco.is_approved:
                eco.state = 'approved'
            elif eco.stage_id.is_approval_required and not eco.is_approved:
                eco.state = 'in_review'
            else:
                eco.state = 'in_review'

    @api.depends('product_id', 'bom_id', 'eco_type', 'version_update')
    def _compute_version_info(self):
        for eco in self:
            cv = '-'
            if eco.eco_type == 'product' and eco.product_id:
                cv = eco.product_id.version or 'v1'
            elif eco.eco_type == 'bom' and eco.bom_id:
                cv = eco.bom_id.version or 'v1'
            eco.current_version = cv

            if eco.version_update and cv != '-':
                try:
                    num = int(cv.lstrip('v'))
                    eco.new_version_label = f'v{num + 1}'
                except ValueError:
                    eco.new_version_label = f'{cv}_new'
            else:
                eco.new_version_label = cv

    @api.depends('product_change_ids', 'bom_change_ids', 'operation_change_ids')
    def _compute_change_count(self):
        for eco in self:
            eco.change_count = (
                len(eco.product_change_ids)
                + len(eco.bom_change_ids)
                + len(eco.operation_change_ids)
            )

    @api.depends('approval_ids')
    def _compute_approval_count(self):
        for eco in self:
            eco.approval_count = len(
                eco.approval_ids.filtered(lambda a: a.state == 'approved')
            )

    @api.depends('audit_log_ids')
    def _compute_audit_count(self):
        for eco in self:
            eco.audit_count = len(eco.audit_log_ids)

    # ══════════════════════════════════════════════════════════════════
    #  onchange helpers
    # ══════════════════════════════════════════════════════════════════

    @api.onchange('eco_type')
    def _onchange_eco_type(self):
        self.product_change_ids = [(5,)]
        self.bom_change_ids = [(5,)]
        self.operation_change_ids = [(5,)]
        if self.eco_type != 'bom':
            self.bom_id = False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.bom_id = False
        self.product_change_ids = [(5,)]
        if self.product_id and self.eco_type == 'product':
            p = self.product_id
            self.product_change_ids = [
                (0, 0, {'field_name': 'name',
                        'field_label': 'Product Name',
                        'old_value': p.name or '',
                        'new_value': p.name or ''}),
                (0, 0, {'field_name': 'sale_price',
                        'field_label': 'Sale Price',
                        'old_value': str(p.sale_price),
                        'new_value': str(p.sale_price)}),
                (0, 0, {'field_name': 'cost_price',
                        'field_label': 'Cost Price',
                        'old_value': str(p.cost_price),
                        'new_value': str(p.cost_price)}),
                (0, 0, {'field_name': 'description',
                        'field_label': 'Description',
                        'old_value': p.description or '',
                        'new_value': p.description or ''}),
            ]

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        self.bom_change_ids = [(5,)]
        self.operation_change_ids = [(5,)]
        if self.bom_id:
            comp_vals = []
            for line in self.bom_id.line_ids:
                comp_vals.append((0, 0, {
                    'component_id': line.component_id.id,
                    'change_type': 'unchanged',
                    'old_qty': line.quantity,
                    'new_qty': line.quantity,
                    'uom': line.uom or '',
                }))
            self.bom_change_ids = comp_vals

            op_vals = []
            for op in self.bom_id.operation_ids:
                op_vals.append((0, 0, {
                    'operation_name': op.name,
                    'work_center': op.work_center,
                    'change_type': 'unchanged',
                    'old_duration': op.duration_minutes,
                    'new_duration': op.duration_minutes,
                }))
            self.operation_change_ids = op_vals

    # ══════════════════════════════════════════════════════════════════
    #  ORM Overrides
    # ══════════════════════════════════════════════════════════════════

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = (
                    self.env['ir.sequence'].next_by_code('plm.eco')
                    or 'ECO/0001'
                )
        records = super().create(vals_list)
        for rec in records:
            rec._log('ECO Created', 'plm.eco', rec.reference, False, rec.name)
        return records

    # ══════════════════════════════════════════════════════════════════
    #  Validation helper
    # ══════════════════════════════════════════════════════════════════

    def _validate_mandatory_fields(self):
        self.ensure_one()
        errors = []
        if not self.name.strip():
            errors.append(_('• ECO Title is required.'))
        if not self.eco_type:
            errors.append(_('• ECO Type is required.'))
        if not self.product_id:
            errors.append(_('• Product is required.'))
        if self.eco_type == 'bom' and not self.bom_id:
            errors.append(_('• Bill of Materials is required for BoM ECOs.'))
        if not self.effective_date:
            errors.append(_('• Effective Date is required.'))
        if errors:
            raise UserError(
                _("Please complete the following mandatory fields before proceeding:\n\n%s")
                % '\n'.join(errors)
            )

    # ══════════════════════════════════════════════════════════════════
    #  Button Actions
    # ══════════════════════════════════════════════════════════════════

    def action_start_review(self):
        """Draft → move to the next stage (In Review / Approval)."""
        self.ensure_one()
        self._validate_mandatory_fields()
        next_stage = self.stage_id._get_next_stage()
        if not next_stage:
            raise UserError(_("No next stage found. Please configure ECO stages in Settings."))
        old = self.stage_id.name
        self.write({'stage_id': next_stage.id, 'kanban_state': 'normal'})
        self._log('Stage Transition', 'plm.eco.stage', self.reference, old, next_stage.name)
        self.message_post(body=_('▶ ECO moved to stage: %s') % next_stage.name)

    def action_request_approval(self):
        """Formally request approval from Approvers."""
        self.ensure_one()
        self._validate_mandatory_fields()
        if not self.stage_id.is_approval_required:
            raise UserError(
                _("The current stage '%s' does not require approval.\n"
                  "Use 'Validate & Apply' instead.") % self.stage_id.name
            )
        # Create approval record
        self.env['plm.eco.approval'].create({
            'eco_id': self.id,
            'requested_by_id': self.env.user.id,
            'state': 'pending',
        })
        self._log('Approval Requested', 'plm.eco', self.reference, 'Draft', 'Pending Approval')
        self.message_post(
            body=_('🔔 Approval requested by %s. '
                   'Awaiting Approver review.') % self.env.user.name
        )
        # Schedule activity for approvers
        approver_group = self.env.ref(
            'plm_engineering.group_plm_approver', raise_if_not_found=False
        )
        if approver_group:
            for user in approver_group.users:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    note=_('ECO "%s" is awaiting your approval.') % self.name,
                )

    def action_approve(self):
        """Approver approves this ECO."""
        self.ensure_one()
        if not (self.env.user.has_group('plm_engineering.group_plm_approver')
                or self.env.user.has_group('plm_engineering.group_plm_manager')):
            raise UserError(_("Only users with the 'Approver' or 'Admin' role can approve ECOs."))

        pending = self.approval_ids.filtered(lambda a: a.state == 'pending')
        if pending:
            pending.write({
                'state': 'approved',
                'reviewed_by_id': self.env.user.id,
                'review_date': fields.Datetime.now(),
                'note': _('Approved by %s') % self.env.user.name,
            })

        self.write({'is_approved': True})
        self._log('ECO Approved', 'plm.eco', self.reference, 'Pending', 'Approved')
        self.message_post(
            body=_('✅ ECO approved by %s.') % self.env.user.name
        )
        # Auto-advance to next stage
        self._advance_stage()

    def action_reject(self):
        """Approver rejects this ECO."""
        self.ensure_one()
        if not (self.env.user.has_group('plm_engineering.group_plm_approver')
                or self.env.user.has_group('plm_engineering.group_plm_manager')):
            raise UserError(_("Only users with the 'Approver' or 'Admin' role can reject ECOs."))

        pending = self.approval_ids.filtered(lambda a: a.state == 'pending')
        pending.write({
            'state': 'rejected',
            'reviewed_by_id': self.env.user.id,
            'review_date': fields.Datetime.now(),
        })
        self.write({'is_approved': False, 'kanban_state': 'blocked'})
        self._log('ECO Rejected', 'plm.eco', self.reference, 'Pending', 'Rejected')
        self.message_post(
            body=_('❌ ECO rejected by %s. '
                   'Please revise and re-submit.') % self.env.user.name
        )

    def action_validate(self):
        """Validate & Apply ECO — applies changes and moves to Done stage."""
        self.ensure_one()
        if self.stage_id.is_approval_required and not self.is_approved:
            raise UserError(
                _("This stage requires approval before validation.\n"
                  "Please request approval first.")
            )
        return self._apply_eco()

    def action_cancel(self):
        """Cancel the ECO and reset to start stage."""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_("A completed ECO cannot be cancelled."))
        start = self.env['plm.eco.stage']._get_start_stage()
        self.approval_ids.filtered(lambda a: a.state == 'pending').write({'state': 'cancelled'})
        self.write({'stage_id': start.id, 'kanban_state': 'blocked', 'is_approved': False})
        self._log('ECO Cancelled', 'plm.eco', self.reference, self.state, 'Cancelled')
        self.message_post(body=_('🚫 ECO has been cancelled.'))

    def action_reset_to_draft(self):
        """Reset ECO back to starting stage."""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_("A completed ECO cannot be reset."))
        start = self.env['plm.eco.stage']._get_start_stage()
        self.approval_ids.filtered(lambda a: a.state in ('pending', 'approved')).write(
            {'state': 'cancelled'}
        )
        self.write({'stage_id': start.id, 'is_approved': False, 'kanban_state': 'normal'})
        self._log('Reset to Draft', 'plm.eco', self.reference, 'Various', 'Draft')
        self.message_post(body=_('🔄 ECO reset to Draft.'))

    def action_view_comparison(self):
        """Open diff-style change comparison wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Change Comparison — %s') % self.name,
            'res_model': 'plm.comparison.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_eco_id': self.id},
        }

    def action_view_audit(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Audit Trail — %s') % self.reference,
            'res_model': 'plm.audit.log',
            'view_mode': 'list,form',
            'domain': [('eco_id', '=', self.id)],
        }

    def action_view_approvals(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Approvals — %s') % self.reference,
            'res_model': 'plm.eco.approval',
            'view_mode': 'list',
            'views': [(self.env.ref('plm_engineering.view_plm_eco_approval_list').id, 'list')],
            'domain': [('eco_id', '=', self.id)],
            'context': {'default_eco_id': self.id},
        }

    # ══════════════════════════════════════════════════════════════════
    #  Private: apply ECO changes
    # ══════════════════════════════════════════════════════════════════

    def _apply_eco(self):
        self.ensure_one()
        if self.eco_type == 'product':
            self._apply_product_changes()
        elif self.eco_type == 'bom':
            self._apply_bom_changes()

        final = self.env['plm.eco.stage']._get_final_stage()
        if final and self.stage_id.id != final.id:
            self.write({'stage_id': final.id})

        self.write({
            'applied_date': fields.Datetime.now(),
            'applied_by_id': self.env.user.id,
        })
        self._log('ECO Applied', 'plm.eco', self.reference, 'Open', 'Done')
        self.message_post(
            body=_(
                '🎉 ECO applied successfully.'
                'Version: %s → %s'
            ) % (self.current_version, self.new_version_label)
        )
        return True

    def _next_version_str(self, current):
        try:
            return 'v' + str(int(current.lstrip('v')) + 1)
        except ValueError:
            return current + '_new'

    def _apply_product_changes(self):
        self.ensure_one()
        p = self.product_id
        if not p:
            return

        # Build vals dict from change lines
        field_map = {
            'name': 'name',
            'sale_price': 'sale_price',
            'cost_price': 'cost_price',
            'description': 'description',
        }
        vals = {}
        for chg in self.product_change_ids.filtered(
            lambda c: c.new_value != c.old_value
        ):
            odoo_field = field_map.get(chg.field_name)
            if not odoo_field:
                continue
            if chg.field_name in ('sale_price', 'cost_price'):
                try:
                    vals[odoo_field] = float(chg.new_value)
                except (ValueError, TypeError):
                    continue
            else:
                vals[odoo_field] = chg.new_value
            self._log('Field Changed', 'plm.product',
                      chg.field_label, chg.old_value, chg.new_value)

        if self.version_update:
            new_ver = self._next_version_str(p.version or 'v1')
            # Create new product version
            new_p_vals = {
                'name': vals.get('name', p.name),
                'sale_price': vals.get('sale_price', p.sale_price),
                'cost_price': vals.get('cost_price', p.cost_price),
                'description': vals.get('description', p.description),
                'internal_ref': p.internal_ref,
                'category': p.category,
                'uom': p.uom,
                'version': new_ver,
                'version_number': (p.version_number or 1) + 1,
                'parent_product_id': p.id,
                'status': 'active',
                'created_by_eco_id': self.id,
            }
            # Use sudo to bypass the write-protection on archived products
            new_p = self.env['plm.product'].sudo().create(new_p_vals)
            # Archive the old version — bypass write protection via sudo
            p.sudo().write({'status': 'archived'})
            self._log('Version Created', 'plm.product',
                      p.name, p.version, new_ver)
            self._log('Version Archived', 'plm.product',
                      p.name, 'Active', 'Archived')
        else:
            if vals:
                # Bypass archived-write-guard using sudo since ECO approval is the gate
                p.sudo().write(vals)

    def _apply_bom_changes(self):
        self.ensure_one()
        bom = self.bom_id
        if not bom:
            return

        if self.version_update:
            new_ver = self._next_version_str(bom.version or 'v1')
            # Deep-copy the BoM
            new_bom = self.env['plm.bom'].sudo().create({
                'name': bom.name,
                'product_id': bom.product_id.id,
                'product_qty': bom.product_qty,
                'version': new_ver,
                'version_number': (bom.version_number or 1) + 1,
                'status': 'active',
                'notes': bom.notes,
                'created_by_eco_id': self.id,
            })

            # Copy existing lines then apply changes
            for line in bom.line_ids:
                self.env['plm.bom.line'].sudo().create({
                    'bom_id': new_bom.id,
                    'component_id': line.component_id.id,
                    'quantity': line.quantity,
                    'note': line.note,
                    'sequence': line.sequence,
                })
            for op in bom.operation_ids:
                self.env['plm.bom.operation'].sudo().create({
                    'bom_id': new_bom.id,
                    'name': op.name,
                    'work_center': op.work_center,
                    'duration_minutes': op.duration_minutes,
                    'note': op.note,
                    'sequence': op.sequence,
                })

            # Apply component changes to new_bom
            self._patch_bom_lines(new_bom)
            self._patch_bom_operations(new_bom)

            # Archive old BoM
            bom.sudo().write({'status': 'archived'})
            self._log('BoM Version Created', 'plm.bom', bom.name, bom.version, new_ver)
            self._log('BoM Archived', 'plm.bom', bom.name, 'Active', 'Archived')
        else:
            self._patch_bom_lines(bom)
            self._patch_bom_operations(bom)

    def _patch_bom_lines(self, bom):
        for chg in self.bom_change_ids:
            existing = bom.line_ids.filtered(
                lambda l: l.component_id.id == chg.component_id.id
            )
            if chg.change_type == 'added':
                if not existing:
                    self.env['plm.bom.line'].sudo().create({
                        'bom_id': bom.id,
                        'component_id': chg.component_id.id,
                        'quantity': chg.new_qty,
                    })
                self._log('Component Added', 'plm.bom.line',
                          chg.component_id.name, '0', str(chg.new_qty))
            elif chg.change_type == 'removed':
                existing.sudo().unlink()
                self._log('Component Removed', 'plm.bom.line',
                          chg.component_id.name, str(chg.old_qty), '0')
            elif chg.change_type == 'modified' and existing:
                existing[0].sudo().write({'quantity': chg.new_qty})
                self._log('Component Modified', 'plm.bom.line',
                          chg.component_id.name, str(chg.old_qty), str(chg.new_qty))

    def _patch_bom_operations(self, bom):
        for chg in self.operation_change_ids:
            existing = bom.operation_ids.filtered(lambda o: o.name == chg.operation_name)
            if chg.change_type == 'added':
                if not existing:
                    self.env['plm.bom.operation'].sudo().create({
                        'bom_id': bom.id,
                        'name': chg.operation_name,
                        'work_center': chg.work_center or '',
                        'duration_minutes': chg.new_duration,
                    })
                self._log('Operation Added', 'plm.bom.operation',
                          chg.operation_name, '0', str(chg.new_duration) + ' min')
            elif chg.change_type == 'removed':
                existing.sudo().unlink()
                self._log('Operation Removed', 'plm.bom.operation',
                          chg.operation_name, str(chg.old_duration) + ' min', '0')
            elif chg.change_type == 'modified' and existing:
                existing[0].sudo().write({'duration_minutes': chg.new_duration})
                self._log('Operation Modified', 'plm.bom.operation',
                          chg.operation_name,
                          str(chg.old_duration) + ' min',
                          str(chg.new_duration) + ' min')

    def _advance_stage(self):
        """Move to the next stage after current."""
        next_s = self.stage_id._get_next_stage()
        if next_s:
            old = self.stage_id.name
            self.write({'stage_id': next_s.id})
            self._log('Stage Transition', 'plm.eco.stage', self.reference, old, next_s.name)
            if next_s.is_final_stage:
                self._apply_eco()

    def _log(self, action, model, record, old_val, new_val):
        self.env['plm.audit.log'].create({
            'eco_id': self.id,
            'action': action,
            'model_name': model,
            'record_name': str(record) if record else '',
            'old_value': str(old_val) if old_val else '',
            'new_value': str(new_val) if new_val else '',
            'user_id': self.env.user.id,
            'timestamp': fields.Datetime.now(),
        })

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env['plm.eco.stage'].search([], order='sequence asc')
