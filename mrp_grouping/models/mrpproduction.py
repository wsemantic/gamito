from odoo import api, fields, models
from datetime import timedelta

import logging
_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    ws_multiplos	= fields.Float('Multiplos', default=1.0)
    wsem_workcenter = fields.Many2one('mrp.workcenter', string='Centro',compute='_compute_wsem_workcenter', store=True)
    wsem_packaging_id = fields.Many2one(
        'product.packaging',
        string='Envasado',
        help='Select the packaging for the production order'
    )
    
    packaging_qty = fields.Float(
        string='Cantidad por bulto',
        related='wsem_packaging_id.qty',
        readonly=True
    )
    
    @api.depends('workorder_ids')
    def _compute_wsem_workcenter(self):
        for production in self:
            if production.workorder_ids:
                production.wsem_workcenter = production.workorder_ids[0].workcenter_id
            else:
                production.wsem_workcenter = False
                
    @api.onchange('ws_multiplos')
    def _onchange_ws_multiplos(self):
        if self.ws_multiplos and self.bom_id:
            newq=self.bom_id.product_qty * self.ws_multiplos
            
            self.qty_producing = newq
            self.product_qty = newq
            

    @api.onchange('product_qty', 'bom_id')
    def _onchange_product_qty(self):
        if self.product_qty and self.bom_id:
            self.ws_multiplos = self.product_qty / self.bom_id.product_qty             
            
    def action_generate_serial(self):
        self.ensure_one()
        
        # Crear los valores del lote
        lot_vals = self._prepare_stock_lot_values()
        
        # Personalización del nombre del lote
        product = self.product_id
        date_now = fields.Datetime.now()
        formatted_date = date_now.strftime("%y%W%w")
        product_ref = product.default_code or 'NO_REF'
        new_lot_name = f"{formatted_date}"
        
        existing_lot = self.env['stock.lot'].search([('name', '=', new_lot_name), ('product_id', '=', product.id)], limit=1)
        if existing_lot:
            # Si existe, usar el lote existente
            _logger.info(f'WSEM v2 ya existía el lote :{new_lot_name}')
            self.lot_producing_id = existing_lot
            return existing_lot
        
        # Si no existe, crear un nuevo lote
        lot_vals['name'] = new_lot_name
        
        # Calculando el 31 de diciembre del próximo año
        current_year = date_now.year
        next_year = current_year + 1
        expiration_date = datetime(next_year, 12, 31)
        
        lot_vals['expiration_date'] = expiration_date
        
        self.lot_producing_id = self.env['stock.lot'].create(lot_vals)
        
        if self.product_id.tracking == 'serial':
            self._set_qty_producing()
        
        _logger.info(f'WSEM v2 asignando nombre lote :{new_lot_name}')
        return self.lot_producing_id