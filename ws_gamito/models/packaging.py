from odoo import models, api

class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    @api.constrains('barcode')
    def _check_barcode_uniqueness(self):
        # Sobrescribimos el método para que no haga ninguna validación.
        pass