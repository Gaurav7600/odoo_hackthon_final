# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta


class PlmDashboard(models.AbstractModel):
    _name = 'plm.dashboard'
    _description = 'PLM Dashboard Data'

    @api.model
    def get_dashboard_data(self):
        today = fields.Date.today()
        now = fields.Datetime.now()
        week_ago = now - timedelta(days=7)
        today_start = datetime.combine(today, datetime.min.time())

        eco_model = self.env['plm.eco']
        stage_model = self.env['plm.eco.stage']
        product_model = self.env['plm.product']
        bom_model = self.env['plm.bom']
        audit_model = self.env['plm.audit.log']

        user = self.env.user
        is_manager = user.has_group('plm_engineering.group_plm_manager')
        is_approver = user.has_group('plm_engineering.group_plm_approver')
        is_engineer = user.has_group('plm_engineering.group_plm_user')
        is_operations_only = (
            user.has_group('plm_engineering.group_plm_operations')
            and not is_engineer
            and not is_approver
            and not is_manager
        )

        state_counts = {
            'draft': 0,
            'in_review': 0,
            'approved': 0,
            'done': 0,
            'cancelled': 0,
        }
        for row in eco_model.read_group([], ['state'], ['state']):
            state = row.get('state')
            count = row.get('state_count', 0)
            if state in state_counts:
                state_counts[state] = count

        total_ecos = sum(state_counts.values())
        pending_approval = state_counts['in_review']

        applied_today = eco_model.search_count([
            ('state', '=', 'done'),
            ('applied_date', '>=', today_start),
        ])
        applied_this_week = eco_model.search_count([
            ('state', '=', 'done'),
            ('applied_date', '>=', week_ago),
        ])

        priority_counts = {'0': 0, '1': 0, '2': 0, '3': 0}
        for row in eco_model.read_group(
            [('state', 'not in', ['done', 'cancelled'])],
            ['priority'],
            ['priority'],
        ):
            priority = row.get('priority')
            count = row.get('priority_count', 0)
            if priority in priority_counts:
                priority_counts[priority] = count

        product_ecos = eco_model.search_count([('eco_type', '=', 'product')])
        bom_ecos = eco_model.search_count([('eco_type', '=', 'bom')])

        stage_count_map = {
            row['stage_id'][0]: row['stage_id_count']
            for row in eco_model.read_group([], ['stage_id'], ['stage_id'])
            if row.get('stage_id')
        }
        stages = stage_model.search([], order='sequence asc, id asc')
        stage_pipeline = [
            {
                'id': stage.id,
                'name': stage.name,
                'count': stage_count_map.get(stage.id, 0),
                'color': stage.color,
                'is_start': stage.is_start_stage,
                'is_final': stage.is_final_stage,
                'is_approval': stage.is_approval_required,
                'fold': stage.fold,
            }
            for stage in stages
        ]

        product_domain = [('status', '=', 'active')] if is_operations_only else []
        bom_domain = [('status', '=', 'active')] if is_operations_only else []

        active_products = product_model.search_count(product_domain + [('status', '=', 'active')])
        archived_products = 0 if is_operations_only else product_model.search_count([('status', '=', 'archived')])

        active_boms = bom_model.search_count(bom_domain + [('status', '=', 'active')])
        archived_boms = 0 if is_operations_only else bom_model.search_count([('status', '=', 'archived')])

        recent_ecos = eco_model.search([], order='create_date desc', limit=8)
        recent_eco_list = [
            {
                'id': eco.id,
                'reference': eco.reference or '',
                'name': eco.name or '',
                'product': eco.product_id.name or '',
                'eco_type': eco.eco_type or '',
                'state': eco.state or 'draft',
                'stage': eco.stage_id.name or '',
                'priority': eco.priority or '0',
                'user': eco.user_id.name or '',
                'effective_date': fields.Date.to_string(eco.effective_date) if eco.effective_date else '',
                'create_date': fields.Datetime.to_string(eco.create_date) if eco.create_date else '',
            }
            for eco in recent_ecos
        ]

        pending_ecos = eco_model.search([('state', '=', 'in_review')], order='create_date desc', limit=5)
        pending_list = [
            {
                'id': eco.id,
                'reference': eco.reference or '',
                'name': eco.name or '',
                'product': eco.product_id.name or '',
                'priority': eco.priority or '0',
                'user': eco.user_id.name or '',
                'effective_date': fields.Date.to_string(eco.effective_date) if eco.effective_date else '',
            }
            for eco in pending_ecos
        ]

        audits = audit_model.search([], order='timestamp desc', limit=5)
        audit_list = [
            {
                'action': audit.action or '',
                'record': audit.record_name or '',
                'user': audit.user_id.name or '',
                'timestamp': fields.Datetime.to_string(audit.timestamp) if audit.timestamp else '',
                'old_value': audit.old_value or '',
                'new_value': audit.new_value or '',
            }
            for audit in audits
        ]

        trend_start = today - timedelta(days=6)
        weekly_trend = []
        for day_offset in range(7):
            day = trend_start + timedelta(days=day_offset)
            day_start = datetime.combine(day, datetime.min.time())
            next_day_start = day_start + timedelta(days=1)
            count = eco_model.search_count([
                ('create_date', '>=', day_start),
                ('create_date', '<', next_day_start),
            ])
            weekly_trend.append({
                'day': day.strftime('%a'),
                'date': fields.Date.to_string(day),
                'count': count,
            })

        my_ecos_count = eco_model.search_count([
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
