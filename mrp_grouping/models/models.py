from odoo import api, fields, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    ws_fecha_grupo = fields.Datetime(string='Fecha Grupo', required=True)