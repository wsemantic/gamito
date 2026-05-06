from odoo import models, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.constrains('barcode')
    def _check_barcode_uniqueness(self):
        # Sobrescribimos el método para que no haga ninguna validación.
        pass