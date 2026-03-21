# -*- coding: utf-8 -*-
{
    'name': 'PLM - Engineering Changes, Executed with Control',
    'version': '18.0.1.0.0',
    'summary': 'Custom PLM: Version-controlled Products, BoMs & ECO Approval Workflows',
    'description': """
        100% Custom PLM Engineering Change Order System
        ================================================
        All models are fully custom — no dependency on product.template or mrp.bom.

        Custom Models:
        - plm.product          : Custom Product Master with versioning
        - plm.bom              : Custom Bill of Materials with versioning
        - plm.bom.line         : BoM Component lines
        - plm.bom.operation    : BoM Operation/Routing lines
        - plm.eco.stage        : Configurable ECO Stages
        - plm.eco              : Engineering Change Order (core)
        - plm.eco.product.change : Product field change lines
        - plm.eco.bom.change   : BoM component change lines
        - plm.eco.operation.change : Operation change lines
        - plm.eco.approval     : Approval records per ECO
        - plm.audit.log        : Immutable audit trail

        Features:
        - Configurable stage pipeline with approval rules
        - Diff-style change comparison (Green/Red/Yellow)
        - Auto version management on ECO apply
        - Role-based access: Engineering, Approver, Operations, Admin
        - Complete audit trail — every action is logged and immutable
        - ECO Reports with clickable change drill-down
    """,
    'author': 'PLM Hackathon Team',
    'category': 'Manufacturing/PLM',
    'depends': ['base', 'mail', 'web'],
    'data': [
        'security/plm_security.xml',
        'security/ir.model.access.csv',
        'data/plm_data.xml',
        'data/plm_demo_data.xml',
        'views/plm_dashboard_views.xml',
        'views/plm_product_views.xml',  
        'views/plm_bom_views.xml',
        'views/plm_eco_stage_views.xml',
        'views/plm_eco_views.xml',
        'views/plm_audit_log_views.xml',
        'views/plm_report_views.xml',
        'wizard/plm_eco_approve_wizard_views.xml',
        'wizard/plm_comparison_wizard_views.xml',
        'views/plm_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'plm_engineering/static/src/css/plm_styles.css',
            'plm_engineering/static/src/xml/plm_dashboard.xml',
            'plm_engineering/static/src/js/plm_dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
