# -*- coding: utf-8 -*-
{
    'name': 'PLM Engineering — Hackathon 2025',
    'version': '18.0.2.0.0',
    'summary': 'Custom PLM: ECO Workflows + Custom Auth Portal (merged)',
    'description': """
        PLM Engineering Change Order System — Odoo Hackathon 2025
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
    'author': 'PLM Hackathon Team',
    'category': 'Manufacturing/PLM',
    'depends': ['base', 'mail', 'web', 'auth_signup'],
    'data': [
        # 1. Security
        'security/plm_security.xml',
        'security/ir.model.access.csv',
        # 2. Seed data
        'data/plm_data.xml',
        'data/signup_approval_data.xml',
        'data/plm_demo_data.xml',
        # 3. PLM backend views
        'views/plm_dashboard_views.xml',
        'views/plm_uom_views.xml',
        'views/plm_product_views.xml',
        'views/plm_bom_views.xml',
        'views/plm_eco_stage_views.xml',
        'views/plm_eco_views.xml',
        'views/plm_eco_comparison_views.xml',
        'views/plm_audit_log_views.xml',
        'views/plm_report_views.xml',
        # 4. Signup approval backend views (includes Settings menu item)
        'views/res_users_approve_views.xml',
        # 5. Menus
        'views/plm_menu.xml',
        # 6. Frontend auth pages (standalone HTML, no website module)
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
        # Auth CSS/JS loaded via <link>/<script> in standalone HTML templates
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
