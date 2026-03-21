# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PlmComparisonWizard(models.TransientModel):
    """
    Diff-style change comparison for ECOs.
    Shows component-wise comparison with Green/Red/Yellow/Neutral indicators.
    """
    _name = 'plm.comparison.wizard'
    _description = 'PLM ECO Change Comparison'

    eco_id = fields.Many2one('plm.eco', required=True)
    eco_type = fields.Selection(related='eco_id.eco_type', readonly=True)
    eco_name = fields.Char(related='eco_id.name', readonly=True)
    eco_reference = fields.Char(related='eco_id.reference', readonly=True)
    current_version = fields.Char(related='eco_id.current_version', readonly=True)
    new_version_label = fields.Char(related='eco_id.new_version_label', readonly=True)

    comparison_html = fields.Html(
        compute='_compute_comparison_html',
        sanitize=False,
        string='Change Comparison',
    )

    @api.depends('eco_id')
    def _compute_comparison_html(self):
        for wiz in self:
            wiz.comparison_html = self._build_html(wiz.eco_id) if wiz.eco_id else ''

    # ──────────────────────────────────────────────────
    def _build_html(self, eco):
        product_name = eco.product_id.display_name_full if eco.product_id else 'N/A'
        eco_type_label = dict(eco._fields['eco_type'].selection).get(eco.eco_type, eco.eco_type)

        html = f"""
<div style="font-family: 'Inter', 'Segoe UI', sans-serif; font-size:14px; color:#212529;">

  <!-- Header card -->
  <div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
              color:white; padding:20px 24px; border-radius:10px; margin-bottom:20px;">
    <div style="font-size:18px; font-weight:700; margin-bottom:6px;">
      Change Comparison Report
    </div>
    <div style="font-size:13px; opacity:0.85; display:flex; gap:24px; flex-wrap:wrap;">
      <span> <b>ECO:</b> {eco.reference} — {eco.name}</span>
      <span> <b>Type:</b> {eco_type_label}</span>
      <span> <b>Product:</b> {product_name}</span>
      <span> <b>Version:</b> {eco.current_version} → {eco.new_version_label}</span>
    </div>
  </div>

  <!-- Legend -->
  <div style="display:flex; gap:10px; margin-bottom:18px; flex-wrap:wrap;">
    <span style="background:#d4edda;color:#155724;padding:4px 14px;border-radius:20px;
                 font-size:12px;font-weight:600;border:1px solid #c3e6cb;">
      ▲ Added / Increased
    </span>
    <span style="background:#f8d7da;color:#721c24;padding:4px 14px;border-radius:20px;
                 font-size:12px;font-weight:600;border:1px solid #f5c6cb;">
      ▼ Reduced / Removed
    </span>
    <span style="background:#fff3cd;color:#856404;padding:4px 14px;border-radius:20px;
                 font-size:12px;font-weight:600;border:1px solid #ffeeba;">
      ✎ Modified
    </span>
    <span style="background:#e9ecef;color:#495057;padding:4px 14px;border-radius:20px;
                 font-size:12px;font-weight:600;border:1px solid #dee2e6;">
      — Unchanged
    </span>
  </div>
"""
        if eco.eco_type == 'product':
            html += self._product_table(eco)
        elif eco.eco_type == 'bom':
            html += self._bom_component_table(eco)
            html += self._bom_operation_table(eco)

        html += '</div>'
        return html

    # ── Product change table ──────────────────────────
    def _product_table(self, eco):
        rows = ''
        for c in eco.product_change_ids:
            bg, icon = self._row_style(c.change_status)
            rows += f"""
  <tr style="{bg}">
    <td style="padding:10px 14px;font-weight:600;">{c.field_label or c.field_name}</td>
    <td style="padding:10px 14px;color:#6c757d;text-decoration:{'line-through' if c.change_status == 'removed' else 'none'};">
      {c.old_value or '—'}
    </td>
    <td style="padding:10px 14px;font-weight:{'700' if c.change_status != 'unchanged' else '400'};">
      {c.new_value or '—'}
    </td>
    <td style="padding:10px 14px;text-align:center;font-size:16px;">{icon}</td>
  </tr>"""

        if not rows:
            rows = '<tr><td colspan="4" style="text-align:center;color:#adb5bd;padding:18px;">No product changes recorded.</td></tr>'

        return f"""
  <div style="font-size:15px;font-weight:700;color:#343a40;margin-bottom:8px;
              padding-bottom:6px;border-bottom:2px solid #dee2e6;">
    Product Field Changes
  </div>
  <table style="width:100%;border-collapse:collapse;margin-bottom:24px;
                border-radius:8px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,0.08);">
    <thead>
      <tr style="background:#212529;color:white;">
        <th style="padding:11px 14px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.06em;">Field</th>
        <th style="padding:11px 14px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.06em;">Current Value</th>
        <th style="padding:11px 14px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.06em;">Proposed Value</th>
        <th style="padding:11px 14px;text-align:center;font-size:12px;text-transform:uppercase;letter-spacing:.06em;">Status</th>
      </tr>
    </thead>
    <tbody style="background:white;">{rows}</tbody>
  </table>"""

    # ── BoM component table ───────────────────────────
    def _bom_component_table(self, eco):
        bom_label = eco.bom_id.display_name_full if eco.bom_id else 'N/A'
        rows = ''
        for c in eco.bom_change_ids:
            bg, icon = self._row_style(c.change_type)
            diff_html = ''
            if c.qty_diff > 0:
                diff_html = f'<span style="color:#28a745;font-weight:700;">+{c.qty_diff:.2f}</span>'
            elif c.qty_diff < 0:
                diff_html = f'<span style="color:#dc3545;font-weight:700;">{c.qty_diff:.2f}</span>'
            else:
                diff_html = '<span style="color:#adb5bd;">0</span>'

            rows += f"""
  <tr style="{bg}">
    <td style="padding:10px 14px;font-weight:600;">{c.component_id.name if c.component_id else '—'}</td>
    <td style="padding:10px 14px;text-align:center;">{c.old_qty:.4f} <small style="color:#adb5bd;">{c.uom or ''}</small></td>
    <td style="padding:10px 14px;text-align:center;font-weight:700;">{c.new_qty:.4f} <small style="color:#adb5bd;">{c.uom or ''}</small></td>
    <td style="padding:10px 14px;text-align:center;">{diff_html}</td>
    <td style="padding:10px 14px;text-align:center;font-size:16px;">{icon}</td>
  </tr>"""

        if not rows:
            rows = '<tr><td colspan="5" style="text-align:center;color:#adb5bd;padding:18px;">No component changes recorded.</td></tr>'

        return f"""
  <div style="font-size:15px;font-weight:700;color:#343a40;margin-bottom:8px;
              padding-bottom:6px;border-bottom:2px solid #dee2e6;">
    Component Changes
    <small style="font-size:12px;color:#6c757d;font-weight:400;margin-left:8px;">BoM: {bom_label}</small>
  </div>
  <table style="width:100%;border-collapse:collapse;margin-bottom:24px;
                border-radius:8px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,0.08);">
    <thead>
      <tr style="background:#212529;color:white;">
        <th style="padding:11px 14px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.06em;">Component</th>
        <th style="padding:11px 14px;text-align:center;font-size:12px;text-transform:uppercase;letter-spacing:.06em;">Current Qty</th>
        <th style="padding:11px 14px;text-align:center;font-size:12px;text-transform:uppercase;letter-spacing:.06em;">Proposed Qty</th>
        <th style="padding:11px 14px;text-align:center;font-size:12px;text-transform:uppercase;letter-spacing:.06em;">Diff</th>
        <th style="padding:11px 14px;text-align:center;font-size:12px;text-transform:uppercase;letter-spacing:.06em;">Status</th>
      </tr>
    </thead>
    <tbody style="background:white;">{rows}</tbody>
  </table>"""

    # ── BoM operation table ───────────────────────────
    def _bom_operation_table(self, eco):
        rows = ''
        for op in eco.operation_change_ids:
            bg, icon = self._row_style(op.change_type)
            diff_html = ''
            if op.duration_diff > 0:
                diff_html = f'<span style="color:#28a745;font-weight:700;">+{op.duration_diff:.1f} min</span>'
            elif op.duration_diff < 0:
                diff_html = f'<span style="color:#dc3545;font-weight:700;">{op.duration_diff:.1f} min</span>'
            else:
                diff_html = '<span style="color:#adb5bd;">0</span>'

            rows += f"""
  <tr style="{bg}">
    <td style="padding:10px 14px;font-weight:600;">{op.operation_name}</td>
    <td style="padding:10px 14px;color:#6c757d;">{op.work_center or '—'}</td>
    <td style="padding:10px 14px;text-align:center;">{op.old_duration:.1f} min</td>
    <td style="padding:10px 14px;text-align:center;font-weight:700;">{op.new_duration:.1f} min</td>
    <td style="padding:10px 14px;text-align:center;">{diff_html}</td>
    <td style="padding:10px 14px;text-align:center;font-size:16px;">{icon}</td>
  </tr>"""

        if not rows:
            rows = '<tr><td colspan="6" style="text-align:center;color:#adb5bd;padding:18px;">No operation changes recorded.</td></tr>'

        return f"""
  <div style="font-size:15px;font-weight:700;color:#343a40;margin-bottom:8px;
              padding-bottom:6px;border-bottom:2px solid #dee2e6;">
    Operation Changes
  </div>
  <table style="width:100%;border-collapse:collapse;margin-bottom:24px;
                border-radius:8px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,0.08);">
    <thead>
      <tr style="background:#212529;color:white;">
        <th style="padding:11px 14px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.06em;">Operation</th>
        <th style="padding:11px 14px;text-align:left;font-size:12px;text-transform:uppercase;letter-spacing:.06em;">Work Center</th>
        <th style="padding:11px 14px;text-align:center;font-size:12px;text-transform:uppercase;letter-spacing:.06em;">Current (min)</th>
        <th style="padding:11px 14px;text-align:center;font-size:12px;text-transform:uppercase;letter-spacing:.06em;">Proposed (min)</th>
        <th style="padding:11px 14px;text-align:center;font-size:12px;text-transform:uppercase;letter-spacing:.06em;">Diff</th>
        <th style="padding:11px 14px;text-align:center;font-size:12px;text-transform:uppercase;letter-spacing:.06em;">Status</th>
      </tr>
    </thead>
    <tbody style="background:white;">{rows}</tbody>
  </table>"""

    # ── Helpers ───────────────────────────────────────
    def _row_style(self, change_type):
        styles = {
            'added':     ('background:#d4edda;border-left:4px solid #28a745;'),
            'removed':   ('background:#f8d7da;border-left:4px solid #dc3545;'),
            'modified':  ('background:#fff3cd;border-left:4px solid #ffc107;'),
            'unchanged': ('background:#f8f9fa;'),
        }
        return styles.get(change_type, ('', '—'))
