# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PlmEcoStage(models.Model):
    """
    Configurable ECO workflow stage.
    Admin can create/reorder stages, mark them as start/final, and set approval rules.
    """
    _name = 'plm.eco.stage'
    _description = 'PLM ECO Stage'
    _order = 'sequence asc, id asc'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description', translate=True)
    color = fields.Integer(string='Color', default=0)
    fold = fields.Boolean(
        string='Folded in Kanban',
        default=False,
        help='Folded stages are collapsed in the Kanban view.',
    )

    # ── Stage Role Flags ─────────────────────────────────────────────
    is_start_stage = fields.Boolean(
        string='Starting Stage',
        default=False,
        help='New ECOs are placed in this stage by default.',
    )
    is_approval_required = fields.Boolean(
        string='Approval Required',
        default=False,
        help='ECOs in this stage must be approved before advancing.\n'
             'An "Approve" button is shown when enabled.\n'
             'A "Validate" button is shown when disabled.',
    )
    is_final_stage = fields.Boolean(
        string='Final / Done Stage',
        default=False,
        help='ECOs reaching this stage are applied: new version becomes active, '
             'old version is archived.',
    )

    # ── Stats ─────────────────────────────────────────────────────────
    eco_count = fields.Integer(
        compute='_compute_eco_count',
        string='ECOs',
    )

    @api.depends()
    def _compute_eco_count(self):
        for stage in self:
            stage.eco_count = self.env['plm.eco'].search_count(
                [('stage_id', '=', stage.id)]
            )

    # ── Helpers ───────────────────────────────────────────────────────
    @api.model
    def _get_start_stage(self):
        start = self.search([('is_start_stage', '=', True)], limit=1)
        if not start:
            start = self.search([], order='sequence asc', limit=1)
        return start

    @api.model
    def _get_final_stage(self):
        return self.search([('is_final_stage', '=', True)], limit=1)

    def _get_next_stage(self):
        """Return the next stage in sequence after self."""
        self.ensure_one()
        return self.search(
            [('sequence', '>', self.sequence)],
            order='sequence asc',
            limit=1,
        )

    # ── Constraints ───────────────────────────────────────────────────
    @api.constrains('is_final_stage')
    def _check_single_final(self):
        for rec in self:
            if rec.is_final_stage:
                others = self.search([
                    ('is_final_stage', '=', True),
                    ('id', '!=', rec.id),
                ])
                if others:
                    raise ValidationError(
                        _("Only one stage can be the Final Stage. "
                        "Please unmark '%s' first.") % others[0].name
                    )

    @api.constrains('is_start_stage')
    def _check_single_start(self):
        for rec in self:
            if rec.is_start_stage:
                others = self.search([
                    ('is_start_stage', '=', True),
                    ('id', '!=', rec.id),
                ])
                if others:
                    raise ValidationError(
                        _("Only one stage can be the Starting Stage. "
                        "Please unmark '%s' first.") % others[0].name
                    )
