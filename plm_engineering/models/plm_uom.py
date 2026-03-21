# -*- coding: utf-8 -*-
from odoo import models, fields


class PlmProductUom(models.Model):
    _name = 'plm.product.uom'
    _description = 'PLM Product Unit of Measure'
    _order = 'sequence, name, id'

    name = fields.Char(
        string='UoM Name',
        required=True,
    )
    code = fields.Char(
        string='Code',
        required=True,
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
