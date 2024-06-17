import logging
from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

   
    ws_bulto_total = fields.Float(string='Total Bultos', compute='_compute_totals', store=True)
    ws_palet_total = fields.Float(string='Total Palets', compute='_compute_totals', store=True)

    @api.depends('move_ids', 'move_ids.product_id', 'move_ids.product_uom_qty', 'move_ids.sale_line_id.product_packaging_qty', 'move_ids.sale_line_id.product_packaging_id.ws_cajas_por_bulto')
    def _compute_totals(self):
        for picking in self:
            total_bulto = 0
            total_palet = 0

            for move_line in picking.move_ids:
                if move_line.sale_line_id.product_packaging_qty > 0:
                    total_bulto += move_line.sale_line_id.product_packaging_qty

                if move_line.sale_line_id.product_packaging_id.ws_cajas_por_bulto > 0:
                    total_palet += move_line.sale_line_id.product_packaging_qty / move_line.sale_line_id.product_packaging_id.ws_cajas_por_bulto

            picking.ws_bulto_total = total_bulto
            picking.ws_palet_total = total_palet