# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta


class PlmDashboard(models.AbstractModel):
    _name = 'plm.dashboard'
    _description = 'PLM Dashboard Data'

    @api.model
    def get_dashboard_data(self):
        EcoModel = self.env['plm.eco']
        ProductModel = self.env['plm.product']
        BomModel = self.env['plm.bom']
        AuditModel = self.env['plm.audit.log']
        StageModel = self.env['plm.eco.stage']

        today = fields.Date.today()
        now = fields.Datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        all_ecos = EcoModel.search([])
        state_counts = {
            'draft': 0,
            'in_review': 0,
            'approved': 0,
            'done': 0,
            'cancelled': 0,
        }
        for eco in all_ecos:
            if eco.state in state_counts:
                state_counts[eco.state] += 1

        total_ecos = len(all_ecos)
        pending_approval = state_counts['in_review']
        applied_today = EcoModel.search_count([
            ('state', '=', 'done'),
            ('applied_date', '>=', fields.Datetime.to_string(
                datetime.combine(today, datetime.min.time())
            )),
        ])
        applied_this_week = EcoModel.search_count([
            ('state', '=', 'done'),
            ('applied_date', '>=', fields.Datetime.to_string(week_ago)),
        ])

        priority_counts = {'0': 0, '1': 0, '2': 0, '3': 0}
        for eco in all_ecos.filtered(lambda e: e.state not in ('done', 'cancelled')):
            if eco.priority in priority_counts:
                priority_counts[eco.priority] += 1

        product_ecos = len(all_ecos.filtered(lambda e: e.eco_type == 'product'))
        bom_ecos = len(all_ecos.filtered(lambda e: e.eco_type == 'bom'))

        stages = StageModel.search([], order='sequence asc')
        stage_pipeline = []
        for stage in stages:
            count = EcoModel.search_count([('stage_id', '=', stage.id)])
            stage_pipeline.append({
                'id': stage.id,
                'name': stage.name,
                'count': count,
                'color': stage.color,
                'is_start': stage.is_start_stage,
                'is_final': stage.is_final_stage,
                'is_approval': stage.is_approval_required,
                'fold': stage.fold,
            })

        active_products = ProductModel.search_count([('status', '=', 'active')])
        archived_products = ProductModel.search_count([('status', '=', 'archived')])
        active_boms = BomModel.search_count([('status', '=', 'active')])
        archived_boms = BomModel.search_count([('status', '=', 'archived')])

        recent_ecos = EcoModel.search([], order='create_date desc', limit=8)
        recent_eco_list = []
        for eco in recent_ecos:
            recent_eco_list.append({
                'id': eco.id,
                'reference': eco.reference or '',
                'name': eco.name or '',
                'product': eco.product_id.name if eco.product_id else '',
                'eco_type': eco.eco_type or '',
                'state': eco.state or 'draft',
                'stage': eco.stage_id.name if eco.stage_id else '',
                'priority': eco.priority or '0',
                'user': eco.user_id.name if eco.user_id else '',
                'effective_date': fields.Date.to_string(eco.effective_date) if eco.effective_date else '',
                'create_date': fields.Datetime.to_string(eco.create_date) if eco.create_date else '',
            })

        pending_ecos = EcoModel.search([('state', '=', 'in_review')], limit=5)
        pending_list = []
        for eco in pending_ecos:
            pending_list.append({
                'id': eco.id,
                'reference': eco.reference or '',
                'name': eco.name or '',
                'product': eco.product_id.name if eco.product_id else '',
                'priority': eco.priority or '0',
                'user': eco.user_id.name if eco.user_id else '',
                'effective_date': fields.Date.to_string(eco.effective_date) if eco.effective_date else '',
            })

        recent_audit = AuditModel.search([], order='timestamp desc', limit=5)
        audit_list = []
        for log in recent_audit:
            audit_list.append({
                'action': log.action or '',
                'record': log.record_name or '',
                'user': log.user_id.name if log.user_id else '',
                'timestamp': fields.Datetime.to_string(log.timestamp) if log.timestamp else '',
                'old_value': log.old_value or '',
                'new_value': log.new_value or '',
            })

        weekly_trend = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_start = fields.Datetime.to_string(
                datetime.combine(day, datetime.min.time())
            )
            day_end = fields.Datetime.to_string(
                datetime.combine(day, datetime.max.time())
            )
            count = EcoModel.search_count([
                ('create_date', '>=', day_start),
                ('create_date', '<=', day_end),
            ])
            weekly_trend.append({
                'day': day.strftime('%a'),
                'date': fields.Date.to_string(day),
                'count': count,
            })

        user = self.env.user
        is_approver = user.has_group('plm_engineering.group_plm_approver')
        is_manager = user.has_group('plm_engineering.group_plm_manager')
        is_engineer = user.has_group('plm_engineering.group_plm_user')

        my_ecos_count = EcoModel.search_count([
            ('user_id', '=', user.id),
            ('state', 'not in', ['done', 'cancelled']),
        ])

        return {
            'total_ecos': total_ecos,
            'pending_approval': pending_approval,
            'applied_today': applied_today,
            'applied_this_week': applied_this_week,
            'active_products': active_products,
            'archived_products': archived_products,
            'active_boms': active_boms,
            'archived_boms': archived_boms,
            'my_ecos_count': my_ecos_count,
            'state_counts': state_counts,
            'priority_counts': priority_counts,
            'product_ecos': product_ecos,
            'bom_ecos': bom_ecos,
            'stage_pipeline': stage_pipeline,
            'recent_ecos': recent_eco_list,
            'pending_list': pending_list,
            'audit_list': audit_list,
            'weekly_trend': weekly_trend,
            'user_name': user.name,
            'is_approver': is_approver,
            'is_manager': is_manager,
            'is_engineer': is_engineer,
            'generated_at': fields.Datetime.to_string(now),
        }
