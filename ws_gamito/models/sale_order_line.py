from odoo import api, models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_price_unit(self):
        for line in self:
            # Verificar si el pedido está confirmado, el producto no ha cambiado y el cliente no ha cambiado
            if (line.order_id.state in ['sale', 'done'] and
                line.product_id == line._origin.product_id and
                line.order_id.partner_id == line._origin.order_id.partner_id):
                continue

            # Si no se cumplen todas las condiciones anteriores, usar el comportamiento estándar
            super(SaleOrderLine, line)._compute_price_unit()