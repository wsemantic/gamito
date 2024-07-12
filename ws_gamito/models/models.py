import logging
from .discount_mixin import DiscountMixin

from odoo import models, fields, api
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)
       

#DESCUENTOS EN PEDIDOS VENTAS Y COMPRAS                    
class SaleOrderLineCustom(models.Model):
    _inherit = 'sale.order.line' 

    def create(self, vals_list):
        # Llama al método super() para ejecutar la lógica original de create        
        
        lines = super(SaleOrderLineCustom, self).create(vals_list)

        # Lógica personalizada después de la creación
        for line in lines:
            line_is_descuento=DiscountMixin.ws_is_desc(line)
            _logger.info(f'WSEM Descuentos pedido create. order {line.order_id.id}')
            if line.order_id and not line._context.get('avoid_recursion'):
                line = line.with_context(avoid_recursion=True)
                DiscountMixin.update_discount_lines(line.order_id, line if line_is_descuento else None)

        return lines    
        
    def write(self, values):       
        # Llama al método super() para ejecutar la lógica original de write
        result = super(SaleOrderLineCustom, self).write(values)        
        
        # Lógica personalizada después de la actualización
        _logger.info(f'WSEM Descuentos pedido write order {self.order_id.id}')
        if self.order_id and not self._context.get('avoid_recursion'):
            self = self.with_context(avoid_recursion=True)
            DiscountMixin.update_discount_lines(self.order_id,None)
            
        return result

class PurchaseOrderLineCustom(models.Model):
    _inherit = 'purchase.order.line'                            
        
    def create(self, vals_list):
        # Llama al método super() para ejecutar la lógica original de create
        lines = super(PurchaseOrderLineCustom, self).create(vals_list)

        # Lógica personalizada después de la creación
        for line in lines:
            _logger.info(f'WSEM Logica personalizada compras después de crear una línea del pedido. order {line.order_id.id}')
            if line.order_id and not line._context.get('avoid_recursion'):
                line = line.with_context(avoid_recursion=True)
                DiscountMixin.update_discount_lines(line.order_id, line)

        return lines 
        
    def write(self, values):       
        # Llama al método super() para ejecutar la lógica original de write
        result = super(PurchaseOrderLineCustom, self).write(values)

        # Lógica personalizada después de la actualización
        _logger.info(f'WSEM Logica personalizada compras después de actualizar las líneas del pedido. order {self.order_id.id}')
        if self.order_id and not self._context.get('avoid_recursion'):
            _logger.info("WSEM Existe orden.")
            self = self.with_context(avoid_recursion=True)
            DiscountMixin.update_discount_lines(self.order_id,None)
            
        return result               

class InvoiceLineCustom(models.Model):
    _inherit = 'account.move.line'

    def create(self, vals_list):
        _logger.info(f'WSEM Descuentos factura ini')
        lines = super(InvoiceLineCustom, self).create(vals_list)
        for line in lines:
            _logger.info(f'WSEM Descuentos factura. move {line.move_id.id}')
            if line.move_id and not line._context.get('avoid_recursion'):
                line = line.with_context(avoid_recursion=True)
                DiscountMixin.update_discount_lines(line.move_id, line)
        return lines

    def write(self, values):       
        result = super(InvoiceLineCustom, self).write(values)
        _logger.info(f'WSEM Descuentos Factura Write linea {self.move_id.id}')
        if self.move_id and not self._context.get('avoid_recursion'):
            _logger.info("WSEM Existe factura.")
            self = self.with_context(avoid_recursion=True)
            DiscountMixin.update_discount_lines(self.move_id, None)
        return result
        
        
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    acc_number = fields.Char(string='Account Number', compute='_compute_acc_number', store=True)

    @api.depends('partner_id.bank_ids')
    def _compute_acc_number(self):
        for line in self:
            bank_accounts = line.partner_id.bank_ids
            if bank_accounts:
                line.acc_number = bank_accounts[0].acc_number  # Obtén el primer número de cuenta bancaria
            else:
                line.acc_number = ''
                
class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    @api.model
    def create(self, vals):
        res = super(ResPartnerBank, self).create(vals)
        self._update_account_move_lines(res.partner_id)
        return res

    def write(self, vals):
        res = super(ResPartnerBank, self).write(vals)
        for bank in self:
            self._update_account_move_lines(bank.partner_id)
        return res

    def _update_account_move_lines(self, partner):
        move_lines = self.env['account.move.line'].search([('partner_id', '=', partner.id)])
        for line in move_lines:
            line._compute_acc_number()