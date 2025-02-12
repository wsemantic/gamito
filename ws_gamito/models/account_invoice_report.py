import logging

from odoo import models, fields, api

class AccountInvoiceReportInherit(models.Model):
    _inherit = "account.invoice.report"

    # Campo previamente añadido para el peso neto
    net_weight = fields.Float(string='Total Kilos Netos', readonly=True)
    # Nuevo campo que mostrará el packaging obtenido desde sale.order.line
    packaging_id = fields.Many2one('product.packaging', string='Packaging', readonly=True)

    _depends = {
        'account.move': [
            'name', 'state', 'move_type', 'partner_id', 'invoice_user_id', 'fiscal_position_id',
            'invoice_date', 'invoice_date_due', 'invoice_payment_term_id', 'partner_bank_id',
        ],
        'account.move.line': [
            'quantity', 'price_subtotal', 'price_total', 'amount_residual', 'balance', 'amount_currency',
            'move_id', 'product_id', 'product_uom_id', 'account_id',
            'journal_id', 'company_id', 'currency_id', 'partner_id',
        ],
        # Se añade la dependencia para que Odoo considere el campo del pedido de venta
        'sale.order.line': ['product_packaging_id'],
        'product.product': ['product_tmpl_id', 'net_weight'],
        'product.template': ['categ_id'],
        'uom.uom': ['category_id', 'factor', 'name', 'uom_type'],
        'res.currency.rate': ['currency_id', 'name'],
        'res.partner': ['country_id'],
    }

    @api.model
    def _select(self):
        # Se extiende la selección original añadiendo el cálculo del net_weight y la obtención del packaging
        return super()._select() + ''',
            (line.quantity * product.net_weight) * 
                (CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END) AS net_weight,
            sol.product_packaging_id AS packaging_id
        '''

    @api.model
    def _from(self):
        # Se extiende la parte FROM de la consulta para unir con la relación de líneas de pedido de venta
        return super()._from() + '''
            LEFT JOIN sale_order_line_invoice_rel sol_rel ON sol_rel.invoice_line_id = line.id
            LEFT JOIN sale_order_line sol ON sol.id = sol_rel.order_line_id
        '''
