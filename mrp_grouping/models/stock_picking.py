import logging, math
from odoo import models, fields, api
_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'
   
    ws_bulto_total = fields.Float(string='Total Bultos', compute='_compute_totals', store=True, readonly=False)
    ws_palet_total = fields.Float(string='Total Palets', compute='_compute_totals', store=True, readonly=False)

    @api.depends('move_ids', 'move_ids.product_id', 'move_ids.product_uom_qty', 'move_ids.sale_line_id.product_packaging_qty', 'move_ids.sale_line_id.product_packaging_id.ws_cajas_por_bulto')
    def _compute_totals(self):
        for picking in self:
            total_bulto = 0
            total_palet = 0
            for move_line in picking.move_ids:
                if move_line.sale_line_id.product_packaging_qty > 0:
                    #cuando se valida un alabran con menos cantidad, y se dice que si a crear una entrega parcial, ODOO divide en dos, en el entregado la demanda y la qty done coincide pero no puedo tirar
                    # de cajas en la linea de pedido que puede ser mayor
                    # Notar que un move line puede tener diferente cantidad que el move debido a diferencia en lote, que es lo que computa en el report de operaciones, pero en el campo de totales solo 
                    # se usa los move, es como decir que en la misma caja puede haber varios lotes
                    
                    total_bulto += move_line.product_uom_qty/move_line.product_packaging_id.qty
                if move_line.sale_line_id.product_packaging_id.ws_cajas_por_bulto > 0:
                    total_palet += move_line.sale_line_id.product_packaging_qty / move_line.sale_line_id.product_packaging_id.ws_cajas_por_bulto

            picking.ws_bulto_total = math.ceil(total_bulto)
            picking.ws_palet_total =  math.ceil(total_palet)
            
            
    @api.model
    def create(self, vals):
        if vals.get('company_id'):
            # Accede directamente a la compañía utilizando browse
            _logger.info(f"WSEM StockPicking tiene company")
            company_b = self.env['res.company'].browse(vals['company_id'])
            
            # Comprueba si es la compañía B
            if company_b.name == 'Test':
                _logger.info(f"WSEM es Test")
                # Cambia la compañía a Company A
                company_a = self.env['res.company'].search([('name', '=', 'Mantecados Gamito Hermanos S.L')], limit=1)
                if company_a:
                    _logger.info(f"WSEM capturada Gamito")
                    vals['company_id'] = company_a.id

        return super(StockPicking, self).create(vals)