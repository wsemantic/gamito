import logging

from odoo import models, fields, api

class AccountInvoiceReportInherit(models.Model):
    _inherit = "account.invoice.report"

    net_weight = fields.Float(string='Total Kilos Netos', readonly=True)
    
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
        'product.product': ['product_tmpl_id', 'weight'],  # Se añade weight aquí
        'product.template': ['categ_id'],
        'uom.uom': ['category_id', 'factor', 'name', 'uom_type'],
        'res.currency.rate': ['currency_id', 'name'],
        'res.partner': ['country_id'],
    }

    @api.model
    def _select(self):
        # Extender la consulta original con super()
        return super()._select() + ''',
            (line.quantity * product.weight)*(CASE WHEN move.move_type IN ('in_invoice','out_refund','in_receipt') THEN -1 ELSE 1 END) AS net_weight
        '''
