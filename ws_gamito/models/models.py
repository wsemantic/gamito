import logging
from .discount_mixin import DiscountMixin

from odoo import models, fields, api
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)

#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    ws_cajas_por_bulto	= fields.Float('Bultos por Palet')
    

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ws_punto_verde	= fields.Float('Punto Verde')
    
'''
Utilizado para buscar solo productos de tu propia empresa, para soportar que empresa codinesa no encuentra productos 
class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        context = self._context

        # Comprobar si la información de la empresa está disponible en el contexto
        new_args = []
        skip_next = False
        for arg in args:
            if skip_next:
                skip_next = False
                continue
            if arg == '|':
                # Verificar si el siguiente par de argumentos es ['company_id', '=', False]
                if args[args.index(arg) + 1] == ['company_id', '=', False]:
                    skip_next = True
                    continue
            new_args.append(arg)

        # Continuar con la lógica de búsqueda
        #_logger.info('WSEM Argumentos de busqueda ProductProduct en _name_search: %s', new_args)
        return super(ProductProduct, self)._name_search(name, args=new_args, operator=operator, limit=limit, name_get_uid=name_get_uid)
 '''       


class SaleOrder(models.Model):
    _inherit = 'sale.order'

#Empresa Test
    @api.onchange('company_id')
    def _onchange_company(self):
        _logger.info("WSEM 1-disparo _onchange_company")
        if self.company_id and self.company_id.name == "Test":            
            new_company_id = self.company_id.id
            _logger.info("WSEM 2- %s ",self.company_id.name)
            for line in self.order_line:
                new_taxes = []
                for tax in line.tax_id:
                    # Buscar un impuesto con el mismo nombre en la nueva compañía
                    new_tax = self.env['account.tax'].search([
                        ('name', '=', tax.name),
                        ('type_tax_use', '=', tax.type_tax_use),
                        ('company_id', '=', new_company_id),
                    ], limit=1)
                    if new_tax:
                        new_taxes.append(new_tax.id)
                # Actualizar los impuestos de la línea con los nuevos impuestos encontrados
                if new_taxes:
                    line.tax_id = [(6, 0, new_taxes)]
            # Buscar y actualizar el almacén si es necesario
            if self.warehouse_id:              
                _logger.info("WSEM 3- Almacen actual %s ",self.warehouse_id.name)            
                # Buscar un almacén en la nueva compañía del mismo tipo
                new_warehouse = self.env['stock.warehouse'].search([
                    ('company_id', '=', new_company_id)
                ], limit=1)
                if new_warehouse:
                    _logger.info("WSEM 4- Almacen nuevo %s ",new_warehouse.name)   
                    self.warehouse_id = new_warehouse.id

class SaleOrderLineCustom(models.Model):
    _inherit = 'sale.order.line' 

    def create(self, vals_list):
        # Llama al método super() para ejecutar la lógica original de create        
        
        lines = super(SaleOrderLineCustom, self).create(vals_list)

        # Lógica personalizada después de la creación
        for line in lines:
            line_is_descuento=DiscountMixin.ws_is_desc(line)
            _logger.info(f'WSEM Logica personalizada ventas después de crear una línea del pedido. order {line.order_id.id}')
            if line.order_id and not line._context.get('avoid_recursion'):
                line = line.with_context(avoid_recursion=True)
                DiscountMixin.update_discount_lines(line.order_id, line if line_is_descuento else None)

        return lines    
        
    def write(self, values):       
        # Llama al método super() para ejecutar la lógica original de write
        result = super(SaleOrderLineCustom, self).write(values)        
        
        # Lógica personalizada después de la actualización
        _logger.info(f'WSEM Logica personalizada ventas después de actualizar las líneas del pedido. order {self.order_id.id}')
        if self.order_id and not self._context.get('avoid_recursion'):
            self = self.with_context(avoid_recursion=True)
            DiscountMixin.update_discount_lines(self.order_id,None);
            
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
            DiscountMixin.update_discount_lines(self.order_id,None);
            
        return result

#from odoo import models, fields, api
#from datetime import datetime
from odoo import models, fields, api
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class StockLot(models.Model):
    _inherit = 'stock.lot'

    @api.model
    def create(self, vals):                
        new_lot_name=False
        expiration_date=False
                
        lot = super(StockLot, self).create(vals)
        product = lot.product_id  # Obtener el objeto producto directamente del lote
        
        _logger.info(f'WSEM create LOTE :{product.name}')
        if not product.name:
            date_now = datetime.now()
            formatted_date = date_now.strftime("%y%W%w")
            product_ref = product.default_code or 'NO_REF'
            new_lot_name=f"{formatted_date}"
            existing_lot = self.env['stock.lot'].search([('name', '=', new_lot_name), ('product_id', '=', product.id)], limit=1)
            if existing_lot:
                # Si existe, usar el lote existente
                _logger.info(f'WSEM ya existía el lote :{new_lot_name}')
                return existing_lot                                                    
                               
        lot.expiration_date = datetime.now() + timedelta(days=450)
        
        if new_lot_name:
            _logger.info(f'WSEM asignando nombre lote :{new_lot_name}')
            lot.name= new_lot_name                                    

        return lot

                

#removal estrategia least_fifo
class StockQuantCustom(models.Model):
    _inherit = 'stock.quant'
    en_consumo_desde = fields.Datetime(
        'Fecha y hora de inicio de consumo',
        default=fields.Datetime.now(),
        required=True,
    )

    def _get_removal_strategy_order(self, removal_strategy):
        if removal_strategy == 'least_fifo_lot':
            return 'en_consumo_desde DESC, in_date ASC, id'
        return super(StockQuantCustom, self)._get_removal_strategy_order(removal_strategy)
        
class StockMoveCustom(models.Model):
    _inherit = 'stock.move'
    
    @api.onchange('lot_ids')
    def _onchange_lot_ids(self):
        _logger.info(f'WSEM cambio de lote')
        result = super()._onchange_lot_ids()

        quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product_id.id),
            ('lot_id', 'in', self.lot_ids.ids),
            ('quantity', '!=', 0),
            ('location_id', '!=', self.location_id.id),
            # Exclude the source location
            ('|', ('location_id.usage', '=', 'customer'), '&', ('company_id', '=', self.company_id.id), ('location_id.usage', 'in', ('internal', 'transit')))])

        if quants:
            for quant in quants:
                if quant.lot_id == self.lot_ids[-1]:
                    quant.en_consumo_desde = fields.Datetime.now()
                    quant.write({'en_consumo_desde': fields.Datetime.now()})

        return result
        
    def write(self, vals):
        # Si se modifica el campo `lot_ids`
        _logger.info(f'WSEM write de lote')         
        if vals.get('move_line_ids'):
            _logger.info(f'WSEM existe campo move_line_ids')
            for command in vals['move_line_ids']:
                if command[0] == 1:  # 1 indica una actualización
                    _logger.info(f'WSEM dentro de campo move_line_ids')
                    move_line_id = command[1]  # ID de la línea de movimiento
                    update_values = command[2]  # Diccionario de valores a actualizar
                    if 'lot_id' in update_values:
                        # Aquí puedes procesar el nuevo valor de lot_id
                        _logger.info(f'WSEM write de lote IN, lot_id: {update_values["lot_id"]}')                
                        # Buscamos el stock quant del lote
                        lot_id_capturado = update_values["lot_id"]
                        extra_domain = [('lot_id', '=', lot_id_capturado)]
                        product_ids=(self.product_id.id,),
                        location_ids=(self.location_id.id,),
                            
                        stock_quants = self.env['stock.quant']._get_quants_by_products_locations(
                            self.product_id,
                            self.location_id,
                            extra_domain=extra_domain
                        )

                        if stock_quants:
                            _logger.info(f'WSEM localizados stocks quants')
                            for stock_quants_group in stock_quants.values():
                                for stock_quant in stock_quants_group:
                                    stock_quant.en_consumo_desde = fields.Datetime.now()

        # Llamamos al método `write` original
        
        res = super(StockMoveCustom, self).write(vals)


        return res
        