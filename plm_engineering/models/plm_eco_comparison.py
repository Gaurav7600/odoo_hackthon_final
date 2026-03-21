# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from markupsafe import Markup


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

    def _badge(self, text, color):
        """Return a small inline badge span."""
        colors = {
            'green':  '#28a745',
            'red':    '#dc3545',
            'orange': '#fd7e14',
            'grey':   '#6c757d',
            'blue':   '#007bff',
        }
        hex_color = colors.get(color, '#6c757d')
        return (
            f'<span style="background:{hex_color};color:#fff;'
            f'padding:2px 8px;border-radius:10px;font-size:11px;'
            f'font-weight:600;white-space:nowrap;">{text}</span>'
        )

    def _row_style(self, change_type):
        """Return inline TR style based on change type."""
        styles = {
            'added':     'background:#e9f7ef;',
            'removed':   'background:#fdecea;',
            'modified':  'background:#fff3e0;',
            'unchanged': 'background:#ffffff;',
        }
        return styles.get(change_type, 'background:#ffffff;')

    def _change_badge(self, change_type):
        """Return colour-coded badge for a change type."""
        cfg = {
            'added':     ('Added',     'green'),
            'removed':   ('Removed',   'red'),
            'modified':  ('Modified',  'orange'),
            'unchanged': ('Unchanged', 'grey'),
        }
        label, color = cfg.get(change_type, ('–', 'grey'))
        return self._badge(label, color)

    def _qty_diff_html(self, old_qty, new_qty, change_type):
        """Render quantity difference with arrow and colour."""
        if change_type == 'unchanged':
            return f'<span style="color:#6c757d;">—</span>'
        diff = new_qty - old_qty
        if diff > 0:
            arrow = '▲'
            color = '#28a745'
        elif diff < 0:
            arrow = '▼'
            color = '#dc3545'
        else:
            arrow = '→'
            color = '#6c757d'
        return (
            f'<span style="color:{color};font-weight:600;">'
            f'{arrow} {abs(diff):g}</span>'
        )

    def _duration_diff_html(self, old_dur, new_dur, change_type):
        """Render duration difference with arrow and colour."""
        if change_type == 'unchanged':
            return f'<span style="color:#6c757d;">—</span>'
        diff = new_dur - old_dur
        if diff > 0:
            arrow = '▲'
            color = '#28a745'
        elif diff < 0:
            arrow = '▼'
            color = '#dc3545'
        else:
            arrow = '→'
            color = '#6c757d'
        return (
            f'<span style="color:{color};font-weight:600;">'
            f'{arrow} {abs(diff):g} min</span>'
        )

    def _section_title(self, title):
        return (
            f'<tr><td colspan="5" style="'
            f'background:#1a1a2e;color:#ffffff;font-size:13px;'
            f'font-weight:700;padding:10px 14px;letter-spacing:0.5px;">'
            f'{title}</td></tr>'
        )

    def _table_header(self, col1, col2, col3, col4='', col5=''):
        cols = [col1, col2, col3]
        if col4:
            cols.append(col4)
        if col5:
            cols.append(col5)
        cells = ''.join(
            f'<th style="padding:8px 12px;background:#f0f0f5;'
            f'color:#333;font-size:12px;text-align:left;'
            f'border-bottom:2px solid #dee2e6;">{c}</th>'
            for c in cols
        )
        return f'<tr>{cells}</tr>'

    def _build_bom_comparison(self, eco):
        """Build HTML for BoM ECO comparison."""
        bom_name = eco.bom_id.name if eco.bom_id else eco.product_id.name
        old_ver = eco.current_version or 'v1'
        new_ver = eco.new_version_label or 'v2'

        added_comps = eco.bom_change_ids.filtered(lambda c: c.change_type == 'added')
        removed_comps = eco.bom_change_ids.filtered(lambda c: c.change_type == 'removed')
        modified_comps = eco.bom_change_ids.filtered(lambda c: c.change_type == 'modified')
        unchanged_comps = eco.bom_change_ids.filtered(lambda c: c.change_type == 'unchanged')

        added_ops = eco.operation_change_ids.filtered(lambda o: o.change_type == 'added')
        removed_ops = eco.operation_change_ids.filtered(lambda o: o.change_type == 'removed')
        modified_ops = eco.operation_change_ids.filtered(lambda o: o.change_type == 'modified')

        html = f'''
<div style="font-family:'Segoe UI',Arial,sans-serif;max-width:900px;margin:0 auto;">

    <div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
            border-radius:10px 10px 0 0;padding:18px 22px;color:#fff;">
    <div style="font-size:18px;font-weight:700;margin-bottom:4px;">
        {bom_name} — ECO Changes
    </div>
    <div style="font-size:12px;opacity:0.8;">
        ECO: <b>{eco.name}</b> &nbsp;|&nbsp;
        Reference: <b>{eco.reference}</b> &nbsp;|&nbsp;
        Version: <b>{old_ver}</b> → <b>{new_ver}</b>
    </div>
</div>

<div style="display:flex;gap:10px;padding:12px 16px;
            background:#f8f9fa;border:1px solid #dee2e6;flex-wrap:wrap;">
    <span style="font-size:12px;color:#555;font-weight:600;align-self:center;">
        Components:</span>
    {self._badge(f"▲ {len(added_comps)} Added", "green") if added_comps else ""}
    {self._badge(f"▼ {len(removed_comps)} Removed", "red") if removed_comps else ""}
    {self._badge(f"~ {len(modified_comps)} Modified", "orange") if modified_comps else ""}
    {self._badge(f"{len(unchanged_comps)} Unchanged", "grey") if unchanged_comps else ""}
    &nbsp;&nbsp;
    <span style="font-size:12px;color:#555;font-weight:600;align-self:center;">
    Operations:</span>
    {self._badge(f"▲ {len(added_ops)} Added", "green") if added_ops else ""}
    {self._badge(f"▼ {len(removed_ops)} Removed", "red") if removed_ops else ""}
    {self._badge(f"~ {len(modified_ops)} Modified", "orange") if modified_ops else ""}
</div>

<div style="display:flex;gap:16px;padding:8px 16px;
            background:#fff;border:1px solid #dee2e6;border-top:none;font-size:11px;border-radius:0 0 10px 10px;">
    <span style="color:#555;font-weight:600;">Legend:</span>
    <span style="background:#e9f7ef;padding:2px 10px;border-radius:4px;
                border-left:4px solid #28a745;color:#155724;">
        Green = Added / Increased</span>
    <span style="background:#fdecea;padding:2px 10px;border-radius:4px;
                border-left:4px solid #dc3545;color:#721c24;">
        Red = Removed / Decreased</span>
    <span style="background:#fff3e0;padding:2px 10px;border-radius:4px;
                border-left:4px solid #fd7e14;color:#856404;">
        Orange = Modified</span>
    <span style="background:#f8f9fa;padding:2px 10px;border-radius:4px;
                border-left:4px solid #6c757d;color:#495057;">
        White = Unchanged</span>
    </div>

<table style="width:100%;border-collapse:collapse;
                border:1px solid #dee2e6;border-top:none;margin-top:15px;">
    {self._section_title("Components")}
    {self._table_header("Component", f"{new_ver} Qty", f"{old_ver} Qty", "Unit", "Δ Diff")}
'''
        if not eco.bom_change_ids:
            html += '''<tr><td colspan="5" style="padding:16px;text-align:center;
                        color:#888;font-style:italic;">
                        No component changes recorded.</td></tr>'''
        else:
            for chg in eco.bom_change_ids:
                ct = chg.change_type
                row_style = self._row_style(ct)
                left_border = ''
                if ct == 'added':
                    left_border = 'border-left:4px solid #28a745;'
                elif ct == 'removed':
                    left_border = 'border-left:4px solid #dc3545;'
                elif ct == 'modified':
                    left_border = 'border-left:4px solid #fd7e14;'
                else:
                    left_border = 'border-left:4px solid transparent;'

                old_qty_str = f'{chg.old_qty:g}' if ct != 'added' else '—'
                new_qty_str = f'{chg.new_qty:g}' if ct != 'removed' else '—'
                diff_html = self._qty_diff_html(chg.old_qty, chg.new_qty, ct)

                if ct == 'added':
                    new_qty_color = 'color:#155724;font-weight:700;'
                    old_qty_color = 'color:#888;'
                elif ct == 'removed':
                    new_qty_color = 'color:#888;'
                    old_qty_color = 'color:#721c24;font-weight:700;text-decoration:line-through;'
                elif ct == 'modified':
                    if chg.new_qty > chg.old_qty:
                        new_qty_color = 'color:#155724;font-weight:700;'
                        old_qty_color = 'color:#721c24;'
                    else:
                        new_qty_color = 'color:#721c24;font-weight:700;'
                        old_qty_color = 'color:#155724;'
                else:
                    new_qty_color = 'color:#333;'
                    old_qty_color = 'color:#333;'

                html += f'''
    <tr style="{row_style}{left_border}border-bottom:1px solid #dee2e6;">
        <td style="padding:9px 12px;font-size:13px;font-weight:600;">
          {self._change_badge(ct)}&nbsp;&nbsp;{chg.component_name or '—'}
        </td>
        <td style="padding:9px 12px;font-size:13px;{new_qty_color}">{new_qty_str}</td>
        <td style="padding:9px 12px;font-size:13px;{old_qty_color}">{old_qty_str}</td>
        <td style="padding:9px 12px;font-size:12px;color:#555;">{chg.product_uom or '—'}</td>
        <td style="padding:9px 12px;">{diff_html}</td>
    </tr>'''

        html += f'''
    {self._section_title("Operations / Routings")}
    {self._table_header("Operation", f"{new_ver} Duration", f"{old_ver} Duration", "Work Center", "Δ Diff")}
'''
        if not eco.operation_change_ids:
            html += '''<tr><td colspan="5" style="padding:16px;text-align:center;
                    color:#888;font-style:italic;">
                    No operation changes recorded.</td></tr>'''
        else:
            for op in eco.operation_change_ids:
                ct = op.change_type
                row_style = self._row_style(ct)
                if ct == 'added':
                    left_border = 'border-left:4px solid #28a745;'
                elif ct == 'removed':
                    left_border = 'border-left:4px solid #dc3545;'
                elif ct == 'modified':
                    left_border = 'border-left:4px solid #fd7e14;'
                else:
                    left_border = 'border-left:4px solid transparent;'

                old_dur = f'{op.old_duration:g} min' if ct != 'added' else '—'
                new_dur = f'{op.new_duration:g} min' if ct != 'removed' else '—'
                diff_html = self._duration_diff_html(op.old_duration, op.new_duration, ct)

                if ct == 'added':
                    new_dur_color = 'color:#155724;font-weight:700;'
                    old_dur_color = 'color:#888;'
                elif ct == 'removed':
                    new_dur_color = 'color:#888;'
                    old_dur_color = 'color:#721c24;font-weight:700;text-decoration:line-through;'
                elif ct == 'modified':
                    if op.new_duration > op.old_duration:
                        new_dur_color = 'color:#155724;font-weight:700;'
                        old_dur_color = 'color:#721c24;'
                    else:
                        new_dur_color = 'color:#721c24;font-weight:700;'
                        old_dur_color = 'color:#155724;'
                else:
                    new_dur_color = 'color:#333;'
                    old_dur_color = 'color:#333;'

                html += f'''
    <tr style="{row_style}{left_border}border-bottom:1px solid #dee2e6;">
    <td style="padding:9px 12px;font-size:13px;font-weight:600;">
        {self._change_badge(ct)}&nbsp;&nbsp;{op.operation_name or '—'}
    </td>
    <td style="padding:9px 12px;font-size:13px;{new_dur_color}">{new_dur}</td>
    <td style="padding:9px 12px;font-size:13px;{old_dur_color}">{old_dur}</td>
    <td style="padding:9px 12px;font-size:12px;color:#555;">{op.work_center or '—'}</td>
    <td style="padding:9px 12px;">{diff_html}</td>
    </tr>'''

        html += '</table></div>'
        return html

    def _build_product_comparison(self, eco):
        """Build HTML for Product ECO comparison."""
        product_name = eco.product_id.name if eco.product_id else 'Product'
        old_ver = eco.current_version or 'v1'
        new_ver = eco.new_version_label or 'v2'

        changed = eco.product_change_ids.filtered(lambda c: c.change_status != 'unchanged')
        unchanged = eco.product_change_ids.filtered(lambda c: c.change_status == 'unchanged')

        html = f'''
<div style="font-family:'Segoe UI',Arial,sans-serif;max-width:900px;margin:0 auto;">

<!-- Header Card -->
<div style="background:linear-gradient(135deg,#0f3460 0%,#16213e 100%);
                border-radius:10px 10px 0 0;padding:18px 22px;color:#fff;">
    <div style="font-size:18px;font-weight:700;margin-bottom:4px;">
        {product_name} — ECO Changes
    </div>
    <div style="font-size:12px;opacity:0.8;">
        ECO: <b>{eco.name}</b> &nbsp;|&nbsp;
        Reference: <b>{eco.reference}</b> &nbsp;|&nbsp;
        Version: <b>{old_ver}</b> → <b>{new_ver}</b>
    </div>
</div>

<div style="display:flex;gap:10px;padding:12px 16px;
            background:#f8f9fa;border:1px solid #dee2e6;flex-wrap:wrap;">
    <span style="font-size:12px;color:#555;font-weight:600;align-self:center;">
        Fields Changed:</span>
    {self._badge(f"{len(changed)} field(s) modified", "blue") if changed else self._badge("No changes", "grey")}
    {self._badge(f"{len(unchanged)} unchanged", "grey") if unchanged else ""}
</div>

    <div style="display:flex;gap:16px;padding:8px 16px;
                background:#fff;border:1px solid #dee2e6;border-top:none;font-size:11px;">
    <span style="color:#555;font-weight:600;">Legend:</span>
    <span style="background:#fff3e0;padding:2px 10px;border-radius:4px;
                border-left:4px solid #fd7e14;color:#856404;">
        Orange = Modified</span>
    <span style="background:#e9f7ef;padding:2px 10px;border-radius:4px;
                border-left:4px solid #28a745;color:#155724;">
        Green = Added</span>
    <span style="background:#fdecea;padding:2px 10px;border-radius:4px;
                border-left:4px solid #dc3545;color:#721c24;">
        Red = Removed</span>
    <span style="background:#f8f9fa;padding:2px 10px;border-radius:4px;
                border-left:4px solid #6c757d;color:#495057;">
        White = Unchanged</span>
    </div>

    <table style="width:100%;border-collapse:collapse;
                border:1px solid #dee2e6;border-top:none;">
    {self._section_title("Product Field Comparison")}
    <tr>
        <th style="padding:8px 12px;background:#f0f0f5;color:#333;
                font-size:12px;text-align:left;border-bottom:2px solid #dee2e6;
                width:20%;">Field</th>
        <th style="padding:8px 12px;background:#e8f5e9;color:#2e7d32;
                font-size:12px;text-align:left;border-bottom:2px solid #dee2e6;
                width:35%;">
        {new_ver} — Proposed Value</th>
        <th style="padding:8px 12px;background:#ffebee;color:#c62828;
                font-size:12px;text-align:left;border-bottom:2px solid #dee2e6;
                width:35%;">
        {old_ver} — Current Value</th>
        <th style="padding:8px 12px;background:#f0f0f5;color:#333;
                font-size:12px;text-align:left;border-bottom:2px solid #dee2e6;
                width:10%;">Status</th>
    </tr>
'''
        if not eco.product_change_ids:
            html += '''<tr><td colspan="4" style="padding:16px;text-align:center;
                        color:#888;font-style:italic;">
                        No product field changes recorded.</td></tr>'''
        else:
            for chg in eco.product_change_ids:
                cs = chg.change_status
                row_style = self._row_style(cs)
                if cs == 'added':
                    left_border = 'border-left:4px solid #28a745;'
                elif cs == 'removed':
                    left_border = 'border-left:4px solid #dc3545;'
                elif cs == 'modified':
                    left_border = 'border-left:4px solid #fd7e14;'
                else:
                    left_border = 'border-left:4px solid transparent;'

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

                if cs == 'modified':
                    new_val_style = 'color:#155724;font-weight:600;'
                    old_val_style = 'color:#721c24;text-decoration:line-through;'
                elif cs == 'added':
                    new_val_style = 'color:#155724;font-weight:600;'
                    old_val_style = 'color:#888;font-style:italic;'
                elif cs == 'removed':
                    new_val_style = 'color:#888;font-style:italic;'
                    old_val_style = 'color:#721c24;font-weight:600;text-decoration:line-through;'
                else:
                    new_val_style = 'color:#333;'
                    old_val_style = 'color:#333;'

                html += f'''
    <tr style="{row_style}{left_border}border-bottom:1px solid #dee2e6;">
        <td style="padding:10px 12px;font-size:13px;font-weight:700;color:#444;">
        {chg.field_label or chg.field_name}
        </td>
        <td style="padding:10px 12px;font-size:13px;{new_val_style}">{new_val_display}</td>
        <td style="padding:10px 12px;font-size:13px;{old_val_style}">{old_val_display}</td>
        <td style="padding:10px 12px;">{self._change_badge(cs)}</td>
    </tr>'''

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
