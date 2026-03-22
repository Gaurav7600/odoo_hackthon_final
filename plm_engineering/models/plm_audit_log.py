# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PlmEcoApproval(models.Model):
    _name = 'plm.eco.approval'
    _description = 'PLM ECO Approval Record'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    eco_id = fields.Many2one('plm.eco', string='ECO', required=True, index=True)
    eco_reference = fields.Char(related='eco_id.reference', string='ECO Reference', store=True, readonly=True)
    requested_by_id = fields.Many2one('res.users', string='Requested By',default=lambda self: self.env.user)
    reviewed_by_id = fields.Many2one('res.users', string='Reviewed By')
    state = fields.Selection([
        ('pending',   'Pending'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status ', default='pending', required=True, tracking=True)

    review_date = fields.Datetime(string='Review Date')
    note = fields.Text(string='Reviewer Note')

    stage_id = fields.Many2one(
        'plm.eco.stage',
        string='Stage at Request',
        related='eco_id.stage_id',
        store=True,
        readonly=True,
    )

    state_display = fields.Char(compute='_compute_state_display', string='Status')

    @api.depends('state')
    def _compute_state_display(self):
        icons = {
            'pending':   ' Pending',
            'approved':  ' Approved',
            'rejected':  ' Rejected',
            'cancelled': ' Cancelled',
        }
        for r in self:
            r.state_display = icons.get(r.state, r.state)


class PlmAuditLog(models.Model):
    _name = 'plm.audit.log'
    _description = 'PLM Audit Log'
    _order = 'timestamp desc, id desc'

    eco_id = fields.Many2one('plm.eco', string='ECO', ondelete='set null', index=True)
    eco_reference = fields.Char(related='eco_id.reference', string='ECO Ref', store=True, readonly=True)
    action = fields.Char(string='Action', required=True, readonly=True)
    model_name = fields.Char(string='Model', readonly=True)
    record_name = fields.Char(string='Record / Field', readonly=True)
    old_value = fields.Char(string='Previous Value', readonly=True)
    new_value = fields.Char(string='New Value', readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True,default=lambda self: self.env.user, readonly=True)
    timestamp = fields.Datetime(string='Timestamp', required=True,default=fields.Datetime.now, readonly=True)

    change_summary = fields.Char(compute='_compute_summary', string='Change Summary')

    @api.depends('old_value', 'new_value')
    def _compute_summary(self):
        for log in self:
            if log.old_value and log.new_value:
                log.change_summary = f'{log.old_value}  -  {log.new_value}'
            elif log.new_value:
                log.change_summary = f'Set: {log.new_value}'
            elif log.old_value:
                log.change_summary = f'Removed: {log.old_value}'
            else:
                log.change_summary = log.action
