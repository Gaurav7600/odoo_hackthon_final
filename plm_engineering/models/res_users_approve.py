# -*- coding: utf-8 -*-
from odoo import fields, models, _
import logging

_logger = logging.getLogger(__name__)


class ResUsersApprove(models.Model):
    _name = 'res.users.approve'
    _description = "Approval Request Details"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', help="Name of the user")
    email = fields.Char(string="Email", help="Email of the user")
    password = fields.Char(string="Password", help="Password of the user")
    for_approval_menu = fields.Boolean(
        string='Approved',
        default=False,
        readonly=True,
        help="True when the registration has been approved by admin")
    approved_date = fields.Datetime(
        string='Approved Date',
        copy=False,
        help="Date when the signup request was approved")
    hide_button = fields.Boolean(
        string='Action Taken',
        default=False,
        help="True when either Approve or Reject has been actioned")

    def action_approve_login(self):
        self.ensure_one()
        user = self.env['res.users'].sudo().search(
            [('login', '=', self.email)], limit=1)
        if not user:
            user = self.env['res.users'].sudo().create({
                'login': self.email,
                'name': self.name,
                'password': self.password,
                'groups_id': [(4, self.env.ref('base.group_portal').id)],
            })

        template = self.env.ref(
            'plm_engineering.mail_template_registration_approved',
            raise_if_not_found=False)
        if template:
            try:
                template.sudo().send_mail(self.id, force_send=True)
            except Exception as e:
                _logger.error("Failed to send approval email: %s", e)

        self.write({
            'for_approval_menu': True,
            'hide_button': True,
            'approved_date': fields.Datetime.now(),
        })

    def action_reject_login(self):
        self.ensure_one()
        user = self.env['res.users'].sudo().search(
            [('login', '=', self.email)], limit=1)
        if user:
            user.sudo().unlink()
        self.write({
            'for_approval_menu': False,
            'hide_button': True,
        })
