# -*- coding: utf-8 -*-
import logging
import werkzeug
from werkzeug.urls import url_encode
from odoo import http, _
from odoo.exceptions import UserError
from odoo.http import request
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.addons.web.controllers.home import ensure_db, Home, LOGIN_SUCCESSFUL_PARAMS

_logger = logging.getLogger(__name__)
LOGIN_SUCCESSFUL_PARAMS.add('account_created')

_APPROVAL_PARAM = 'plm_engineering.auth_signup_approval'
_DASHBOARD_URL  = '/odoo/action-plm_engineering.action_plm_dashboard'
_PLM_BASE_GROUP = 'plm_engineering.group_plm_operations'


class AuthSignupHome(Home):
    """
    PLM Engineering — custom login / signup controller.
    No website module dependency. Approval always on.
    After login, PLM users are redirected to the PLM Dashboard.
    """

    @staticmethod
    def _is_redirect(response):
        return (
            isinstance(response, werkzeug.wrappers.Response)
            and response.status_code in (301, 302, 303, 307, 308)
        )

    def _pending_approval(self, email):
        if not email:
            return False
        return bool(
            request.env['res.users.approve'].sudo().search([
                ('email', '=', email),
                ('for_approval_menu', '=', False),
                ('hide_button', '=', False),
            ], limit=1)
        )

    def _has_plm_access(self):
        try:
            return request.env.user.has_group(_PLM_BASE_GROUP)
        except Exception:
            return False

    # ── LOGIN ──────────────────────────────────────────────────────────────────

    @http.route()
    def web_login(self, redirect=None, **kw):
        ensure_db()

        if request.session.uid:
            return super().web_login(redirect=redirect, **kw)

        qcontext = self.get_auth_signup_qcontext()

        if request.httprequest.method == 'POST':
            login_email = request.params.get('login', '').strip()

            if self._pending_approval(login_email):
                return request.redirect('/wait-approval')

            response = super().web_login(redirect=redirect, **kw)

            if self._is_redirect(response):
                if self._has_plm_access():
                    return request.redirect(_DASHBOARD_URL)
                return response

            qcontext = self.get_auth_signup_qcontext()
            if not qcontext.get('error'):
                qcontext['error'] = _("Wrong login/password.")

        response = request.render('plm_engineering.custom_login_page', qcontext)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    # ── SIGNUP ─────────────────────────────────────────────────────────────────

    @http.route('/web/signup', type='http', auth='public', sitemap=False)
    def web_auth_signup(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()

        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()

        signup_approval = request.env['ir.config_parameter'].sudo().get_param(
            _APPROVAL_PARAM, default='True')

        if 'error' not in qcontext and request.httprequest.method == 'POST':

            if signup_approval:
                name     = qcontext.get('name', '').strip()
                email    = qcontext.get('login', '').strip()
                password = qcontext.get('password', '')

                if not name or not email or not password:
                    qcontext['error'] = _("Please fill in all required fields.")
                else:
                    existing = request.env['res.users.approve'].sudo().search(
                        [('email', '=', email)], limit=1)
                    if existing:
                        qcontext['error'] = _(
                            "A registration request with this email already "
                            "exists. Please wait for approval or contact us.")
                    else:
                        try:
                            approve_rec = request.env[
                                'res.users.approve'].sudo().create({
                                'name': name, 'email': email, 'password': password,
                            })
                            template = request.env.ref(
                                'plm_engineering.mail_template_waiting_approval',
                                raise_if_not_found=False)
                            if template:
                                template.sudo().send_mail(
                                    approve_rec.id, force_send=True)
                            return request.redirect('/success')
                        except Exception as e:
                            _logger.error("PLM signup error: %s", e)
                            qcontext['error'] = _(
                                "Could not submit your registration. Please try again.")
            else:
                try:
                    self.do_signup(qcontext)
                    if qcontext.get('token'):
                        user = request.env['res.users']
                        user_sudo = user.sudo().search(
                            user._get_login_domain(qcontext.get('login')),
                            order=user._get_login_order(), limit=1)
                        template = request.env.ref(
                            'auth_signup.mail_template_user_signup_account_created',
                            raise_if_not_found=False)
                        if user_sudo and template:
                            template.sudo().send_mail(user_sudo.id, force_send=True)
                    return self.web_login(*args, **kw)
                except UserError as e:
                    qcontext['error'] = e.args[0]
                except (SignupError, AssertionError) as e:
                    if request.env["res.users"].sudo().search(
                            [("login", "=", qcontext.get("login"))]):
                        qcontext["error"] = _(
                            "Another user is already registered using this email address.")
                    else:
                        _logger.error("%s", e)
                        qcontext['error'] = _("Could not create a new account.")

        elif 'signup_email' in qcontext:
            user = request.env['res.users'].sudo().search(
                [('email', '=', qcontext.get('signup_email')),
                 ('state', '!=', 'new')], limit=1)
            if user:
                return request.redirect('/web/login?%s' % url_encode(
                    {'login': user.login, 'redirect': '/web'}))

        response = request.render('plm_engineering.custom_signup_page', qcontext)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    # ── STATUS PAGES ───────────────────────────────────────────────────────────

    @http.route('/success', type='http', auth='public', sitemap=False)
    def approval_success(self):
        return request.render("plm_engineering.approval_form_success")

    @http.route('/wait-approval', type='http', auth='public', sitemap=False)
    def wait_for_approval(self):
        return request.render("plm_engineering.wait_for_approval_page")
