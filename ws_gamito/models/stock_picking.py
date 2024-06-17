import logging
from .stock_picking import StockPicking
from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    ws_bulto_total = fields.Float(string='Total Bultos')
    ws_palet_total = fields.Float(string='Total Palets')
    
    ws_bulto_total = fields.Float(string='Total Bultos', compute='_compute_totals', store=True)
    ws_palet_total = fields.Float(string='Total Palets', compute='_compute_totals', store=True)

    @api.depends('move_ids', 'move_ids.product_id', 'move_ids.product_uom_qty', 'move_ids.sale_line_id.product_packaging_qty', 'move_ids.sale_line_id.product_packaging_id.ws_cajas_por_bulto')
    def _compute_totals(self):
        for picking in self:
            total_net_weight = 0
            total_weight = 0
            total_bulto = 0
            total_palet = 0

            for move_line in picking.move_ids:
                product_net_weight = move_line.product_id.product_tmpl_id.net_weight or 0
                total_net_weight += product_net_weight * move_line.product_uom_qty

                product_weight = move_line.product_id.product_tmpl_id.weight or 0
                total_weight += product_weight * move_line.product_uom_qty

                if move_line.sale_line_id.product_packaging_qty > 0:
                    total_bulto += move_line.sale_line_id.product_packaging_qty

                if move_line.sale_line_id.product_packaging_id.ws_cajas_por_bulto > 0:
                    total_palet += move_line.sale_line_id.product_packaging_qty / move_line.sale_line_id.product_packaging_id.ws_cajas_por_bulto

            picking.total_net_weight = total_net_weight
            picking.total_weight = total_weight
            picking.ws_bulto_total = total_bulto
            picking.ws_palet_total = total_palet