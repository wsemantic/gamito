from odoo import models, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.constrains('barcode')
    def _check_barcode_uniqueness(self):
        # Sobrescribimos el método para que no haga ninguna validación.
        pass

    def action_product_tmpl_forecast_report(self):
        self.ensure_one()
        return self.product_tmpl_id.action_product_tmpl_forecast_report()