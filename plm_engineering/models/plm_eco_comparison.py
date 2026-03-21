# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from markupsafe import Markup, escape


class PlmEcoComparisonWizard(models.TransientModel):
    _name = 'plm.eco.comparison.wizard'
    _description = 'ECO Versioned Change Comparison'

    eco_id = fields.Many2one(
        'plm.eco',
        string='ECO',
        required=True,
        ondelete='cascade',
    )
    eco_name = fields.Char(related='eco_id.name', string='ECO Title', readonly=True)
    eco_type = fields.Selection(related='eco_id.eco_type', string='ECO Type', readonly=True)
    current_version = fields.Char(
        related='eco_id.current_version', string='Current Version', readonly=True
    )
    new_version_label = fields.Char(
        related='eco_id.new_version_label', string='New Version', readonly=True
    )

    comparison_html = fields.Html(
        string='Change Comparison',
        compute='_compute_comparison_html',
        sanitize=False,
    )

    def _simple_badge(self, change_type):
        labels = {
            'added': 'Added',
            'removed': 'Removed',
            'modified': 'Modified',
            'unchanged': 'Unchanged',
        }
        label = labels.get(change_type, 'Unknown')
        return (
            '<span style="display:inline-block;padding:1px 8px;'
            'border:1px solid #d0d0d0;border-radius:10px;'
            'font-size:11px;font-weight:600;background:#f7f7f7;color:#333;">'
            f'{escape(label)}</span>'
        )

    def _simple_table_header(self, columns):
        cells = ''.join(
            (
                '<th style="padding:8px;border:1px solid #dcdcdc;'
                'background:#f5f5f5;text-align:left;font-size:12px;">'
                f'{escape(col)}</th>'
            )
            for col in columns
        )
        return f'<tr>{cells}</tr>'

    def _simple_table_row(self, cells):
        values = ''.join(
            (
                '<td style="padding:8px;border:1px solid #e6e6e6;'
                'vertical-align:top;font-size:12px;">'
                f'{value}</td>'
            )
            for value in cells
        )
        return f'<tr>{values}</tr>'

    def _diff_value(self, old_val, new_val, change_type, suffix=''):
        if change_type == 'unchanged':
            return '—'
        if change_type == 'added':
            return f'+{new_val:g}{suffix}'
        if change_type == 'removed':
            return f'-{old_val:g}{suffix}'
        diff = new_val - old_val
        sign = '+' if diff > 0 else ''
        return f'{sign}{diff:g}{suffix}'

    def _build_bom_comparison(self, eco):
        """Build HTML for BoM ECO comparison."""
        bom_name = eco.bom_id.name if eco.bom_id else eco.product_id.name
        old_ver = eco.current_version or 'v1'
        new_ver = eco.new_version_label or 'v2'

        html = f'''
<div style="font-family:Arial, sans-serif;">
    <div style="margin-bottom:10px;">
        <strong>{escape(bom_name)} — ECO Changes</strong><br/>
        ECO: {escape(eco.name or '—')} | Reference: {escape(eco.reference or '—')} | Version: {escape(old_ver)} → {escape(new_ver)}
    </div>

    <div style="margin:8px 0 4px 0;"><strong>Components</strong></div>
    <table style="width:100%;border-collapse:collapse;">
        {self._simple_table_header(['Change', 'Component', f'{new_ver} Qty', f'{old_ver} Qty', 'Unit', 'Diff'])}
'''
        if not eco.bom_change_ids:
            html += self._simple_table_row([
                '<span style="color:#777;">No component changes recorded.</span>', '', '', '', '', ''
            ])
        else:
            for chg in eco.bom_change_ids:
                ct = chg.change_type
                old_qty_str = f'{chg.old_qty:g}' if ct != 'added' else '—'
                new_qty_str = f'{chg.new_qty:g}' if ct != 'removed' else '—'
                html += self._simple_table_row([
                    self._simple_badge(ct),
                    escape(chg.component_name or '—'),
                    escape(new_qty_str),
                    escape(old_qty_str),
                    escape(chg.product_uom or '—'),
                    escape(self._diff_value(chg.old_qty, chg.new_qty, ct)),
                ])

        html += f'''
    </table>

    <div style="margin:14px 0 4px 0;"><strong>Operations / Routings</strong></div>
    <table style="width:100%;border-collapse:collapse;">
        {self._simple_table_header(['Change', 'Operation', f'{new_ver} Duration', f'{old_ver} Duration', 'Work Center', 'Diff'])}
'''
        if not eco.operation_change_ids:
            html += self._simple_table_row([
                '<span style="color:#777;">No operation changes recorded.</span>', '', '', '', '', ''
            ])
        else:
            for op in eco.operation_change_ids:
                ct = op.change_type
                old_dur = f'{op.old_duration:g} min' if ct != 'added' else '—'
                new_dur = f'{op.new_duration:g} min' if ct != 'removed' else '—'
                html += self._simple_table_row([
                    self._simple_badge(ct),
                    escape(op.operation_name or '—'),
                    escape(new_dur),
                    escape(old_dur),
                    escape(op.work_center or '—'),
                    escape(self._diff_value(op.old_duration, op.new_duration, ct, ' min')),
                ])

        html += '</table></div>'
        return html

    def _build_product_comparison(self, eco):
        """Build HTML for Product ECO comparison."""
        product_name = eco.product_id.name if eco.product_id else 'Product'
        old_ver = eco.current_version or 'v1'
        new_ver = eco.new_version_label or 'v2'

        html = f'''
<div style="font-family:Arial, sans-serif;">
    <div style="margin-bottom:10px;">
        <strong>{escape(product_name)} — ECO Changes</strong><br/>
        ECO: {escape(eco.name or '—')} | Reference: {escape(eco.reference or '—')} | Version: {escape(old_ver)} → {escape(new_ver)}
    </div>

    <div style="margin:8px 0 4px 0;"><strong>Product Field Comparison</strong></div>
    <table style="width:100%;border-collapse:collapse;">
        {self._simple_table_header(['Change', 'Field', f'{new_ver} Value', f'{old_ver} Value'])}
'''
        if not eco.product_change_ids:
            html += self._simple_table_row([
                '<span style="color:#777;">No product field changes recorded.</span>', '', '', ''
            ])
        else:
            for chg in eco.product_change_ids:
                cs = chg.change_status
                new_val = chg.new_value or '—'
                old_val = chg.old_value or '—'

                if len(str(new_val)) > 80:
                    new_val_display = str(new_val)[:77] + '...'
                else:
                    new_val_display = str(new_val)
                if len(str(old_val)) > 80:
                    old_val_display = str(old_val)[:77] + '...'
                else:
                    old_val_display = str(old_val)

                html += self._simple_table_row([
                    self._simple_badge(cs),
                    escape(chg.field_label or chg.field_name or '—'),
                    escape(new_val_display),
                    escape(old_val_display),
                ])

        html += '</table></div>'
        return html

    @api.depends('eco_id', 'eco_id.bom_change_ids', 'eco_id.product_change_ids',
                'eco_id.operation_change_ids')
    def _compute_comparison_html(self):
        for rec in self:
            if not rec.eco_id:
                rec.comparison_html = Markup('<p>No ECO selected.</p>')
                continue
            if rec.eco_id.eco_type == 'bom':
                html = rec._build_bom_comparison(rec.eco_id)
            elif rec.eco_id.eco_type == 'product':
                html = rec._build_product_comparison(rec.eco_id)
            else:
                html = '<p style="color:#888;">Unknown ECO type.</p>'
            rec.comparison_html = Markup(html)

    @api.model
    def action_open_for_eco(self, eco_id):
        """Create wizard record and return action to open it."""
        wizard = self.create({'eco_id': eco_id})
        return {
            'type': 'ir.actions.act_window',
            'name': _('Versioned Change Comparison'),
            'res_model': 'plm.eco.comparison.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'form_view_initial_mode': 'readonly'},
        }
