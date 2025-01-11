from odoo import models, api

class ProductPackaging(models.Model):
    _inherit = 'product.packaging'
    
    _sql_constraints = [
        ('positive_qty', 'CHECK(qty > 0)', 'Contained Quantity should be positive.'),
        # Nota: Hemos eliminado 'barcode_uniq'
    ]

    @api.constrains('barcode')
    def _check_barcode_uniqueness(self):
        # Sobrescribimos el método para que no haga ninguna validación.
        pass
