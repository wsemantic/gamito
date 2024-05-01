from odoo import api, fields, models

import logging
_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    ws_multiplos	= fields.Float('Multiplos', default=1.0)
    wsem_workcenter = fields.Many2one('mrp.workcenter', string='Centro',compute='_compute_wsem_workcenter', store=True)

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