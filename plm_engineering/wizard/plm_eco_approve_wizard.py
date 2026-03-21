# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PlmEcoApproveWizard(models.TransientModel):
    """Confirmation wizard shown before validating & applying an ECO."""
    _name = 'plm.eco.approve.wizard'
    _description = 'Validate & Apply ECO Wizard'

    eco_id = fields.Many2one('plm.eco', required=True)

    # Mirror key info for display
    eco_name = fields.Char(related='eco_id.name', readonly=True)
    eco_reference = fields.Char(related='eco_id.reference', readonly=True)
    eco_type = fields.Selection(related='eco_id.eco_type', readonly=True)
    product_name = fields.Char(
        compute='_compute_product_name', string='Product', readonly=True,
    )
    current_version = fields.Char(related='eco_id.current_version', readonly=True)
    new_version_label = fields.Char(related='eco_id.new_version_label', readonly=True)
    version_update = fields.Boolean(related='eco_id.version_update', readonly=True)
    change_count = fields.Integer(related='eco_id.change_count', readonly=True)

    confirm_ref = fields.Char(
        string='Type Reference to Confirm',
        help='Type the ECO reference exactly to confirm the irreversible action.',
    )
    closing_note = fields.Text(
        string='Closing Note',
        help='Optional note attached to this ECO on closure.',
    )
    warning_msg = fields.Char(
        compute='_compute_warning', string='Warning',
    )

    @api.depends('eco_id')
    def _compute_product_name(self):
        for w in self:
            w.product_name = w.eco_id.product_id.display_name_full if w.eco_id.product_id else '-'

    @api.depends('eco_id', 'version_update', 'current_version', 'new_version_label')
    def _compute_warning(self):
        for w in self:
            if w.version_update:
                w.warning_msg = (
                    f"A new version '{w.new_version_label}' will be created. "
                    f"Version '{w.current_version}' will be archived. "
                    "This action cannot be undone."
                )
            else:
                w.warning_msg = (
                    f"Changes will be applied directly to version '{w.current_version}'. "
                    "No new version will be created. This action cannot be undone."
                )

    def action_confirm(self):
        self.ensure_one()
        if self.confirm_ref and self.confirm_ref.strip() != (self.eco_reference or '').strip():
            raise UserError(
                _("Reference mismatch. Please type '%s' exactly to confirm.")
                % self.eco_reference
            )
        if self.closing_note:
            self.eco_id.message_post(
                body=_('📝 Closing Note: %s') % self.closing_note
            )
        return self.eco_id.action_validate()
