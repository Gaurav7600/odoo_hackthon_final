# -*- coding: utf-8 -*-
{
    'name': 'PLM Engineering',
    'version': '18.0.2.0.0',
    'summary': 'Custom PLM: ECO Workflows + Custom Auth Portal',
    'description': """
        PLM Engineering Change Order System
        ==========================================================
        Single self-contained module. No dependency on website/website_sale.

        Includes:
        ─ Custom glassmorphism login & signup pages
        ─ Signup approval queue (admin approves before user can log in)
        ─ Auto-redirect to PLM Dashboard after login
        ─ Role-based dashboard: Operations / Engineer / Approver / Admin
        ─ Version-controlled Products & BoMs
        ─ Configurable ECO stage pipeline with approval rules
        ─ Diff-style change comparison
        ─ Auto version bump on ECO apply
        ─ Immutable audit trail
    """,
    'author': 'Coding War Team',
    'category': 'Manufacturing/PLM',
    'depends': ['base', 'mail', 'web', 'auth_signup'],
    'data': [
        'security/plm_security.xml',
        'security/ir.model.access.csv',
        'data/plm_data.xml',
        'data/signup_approval_data.xml',
        'data/plm_demo_data.xml',
        'views/plm_dashboard_views.xml',
        'views/plm_uom_views.xml',
        'views/plm_product_views.xml',
        'views/plm_bom_views.xml',
        'views/plm_eco_stage_views.xml',
        'views/plm_eco_views.xml',
        'views/plm_eco_comparison_views.xml',
        'views/plm_audit_log_views.xml',
        'views/plm_report_views.xml',
        'views/res_users_approve_views.xml',
        'views/plm_menu.xml',
        'views/login_signup_templates.xml',
        'views/approval_request_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'plm_engineering/static/src/css/plm_styles.css',
            'plm_engineering/static/src/xml/plm_dashboard.xml',
            'plm_engineering/static/src/xml/plm_sidebar.xml',
            'plm_engineering/static/src/js/plm_sidebar.js',
            'plm_engineering/static/src/js/plm_dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
