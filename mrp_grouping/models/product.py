import logging

from odoo import models, fields, api
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)

#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    ws_cajas_por_bulto	= fields.Float('Bultos por Palet')
    

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ws_punto_verde	= fields.Float('Punto Verde')