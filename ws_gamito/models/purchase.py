from odoo import models, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('move_ids.state', 'move_ids.product_uom_qty', 'move_ids.product_uom')
    def _compute_qty_received(self):
        # Primero ejecutamos el cálculo estándar
																											
        super(PurchaseOrderLine, self)._compute_qty_received()
        
        # Luego corregimos específicamente para casos de devolución
        for line in self:
            if line.product_id.type in ['consu', 'product'] and line.qty_received == 0 and line.order_id.state in ['purchase', 'done']:
                # Buscamos movimientos de devolución (OUT hacia supplier)
                return_moves = line.move_ids.filtered(
			
					   
                    lambda m: m.state == 'done' and 
                    not m.scrapped and 
                    m.location_dest_id.usage == "supplier"
                )
                
                if return_moves:
                    # Calculamos la cantidad devuelta
                    qty_returned = sum(
                        move.product_uom._compute_quantity(move.product_uom_qty, line.product_uom)
                        for move in return_moves
                    )
                    # Actualizamos qty_received con valor negativo
                    line.qty_received = -qty_returned