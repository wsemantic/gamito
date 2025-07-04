from odoo import models, fields, api
import logging
import re

_logger = logging.getLogger(__name__)

class ResPartnerDiscount(models.Model):
    _name = 'res.partner.discount'
    _description = 'DESCUENTOS'

    name = fields.Char(string='Nombre', required=True)
    discount_percent = fields.Float(string='Porcentaje', required=True)
    partner_id = fields.Many2one('res.partner', string='Customer', ondelete='cascade')


#de momento solo tiene en cuenta descuentos prefijados en partner para las ventas, solo la linea de venta (pedido y factura) memoriza el id descuento asignado desde el partner
# para distinguir los añadidos extras en la sesion de edicion del documento, y no volverlo a añadir (no veo el conflicto, solo lo veo util por si el usuario modifica demasiado la descripcion)
class ResPartner(models.Model):
    _inherit = 'res.partner'
    discount_ids = fields.One2many('res.partner.discount', 'partner_id', string='Descuentos')
    
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create(self, vals):
        order = super(SaleOrder, self).create(vals)
        DiscountMixin._apply_discounts(order)
        return order

    def write(self, vals):      
        res = super(SaleOrder, self).write(vals)
        _logger.info(f'WSEM ORDER write descuentos llamado')
        DiscountMixin._apply_discounts(self)
        return res    
        
class AccountMove(models.Model):
    _inherit = 'account.move'
    discounts_initialized = fields.Boolean(string='Discounts Initialized', default=False)
    
    @api.model
    def create(self, vals):
        move = super(AccountMove, self).create(vals)
        #DiscountMixin._apply_discounts(move)
        return move

    def write(self, vals):    
        if self.env.context.get('prevent_recursion'):
            return super(AccountMove, self).write(vals)
        
        self = self.with_context(prevent_recursion=True)
        res = super(AccountMove, self).write(vals)

        # Iterar sobre cada registro en caso de múltiples registros
        for record in self:
            if not record.discounts_initialized:
                record._initialize_discount_ids()
            DiscountMixin._apply_discounts(record)
            if hasattr(record, '_onchange_invoice_line_ids'):
                _logger.info("WSEM existe atributo onchange_invoice")
                record._onchange_invoice_line_ids()

        return res        
        
    def _initialize_discount_ids(self):    
        if self.discounts_initialized:
            return
        partner_id = self.partner_id.id if self.partner_id else None
        if not partner_id:
            _logger.info("WSEM No partner found for record")
            return

        discounts = self.env['res.partner.discount'].search([('partner_id', '=', partner_id)])
        if not discounts:
            _logger.info("No discounts found for partner")
            return

        for line in self.invoice_line_ids:
            if not line.discount_id:
                matching_discount = discounts.filtered(lambda d: line.name and line.name.startswith(d.name))
                if matching_discount:
                    line.discount_id = matching_discount[0].id
                    _logger.info(f"WSEM Assigned discount {matching_discount[0].name} to line {line.name}")
        self.discounts_initialized = True
                    
#DESCUENTOS EN PEDIDOS VENTAS Y COMPRAS                    
class SaleOrderLineCustom(models.Model):
    _inherit = 'sale.order.line' 
    discount_id = fields.Many2one('res.partner.discount', string='Discount ID')

    '''def create(self, vals_list):
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
        '''

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
                DiscountMixin.update_discount_lines(line.order_id, line, 'in')

        return lines 
        
    def write(self, values):       
        # Llama al método super() para ejecutar la lógica original de write
        result = super(PurchaseOrderLineCustom, self).write(values)

        # Lógica personalizada después de la actualización
        _logger.info(f'WSEM Logica personalizada compras después de actualizar las líneas del pedido. order {self.order_id.id}')
        if self.order_id and not self._context.get('avoid_recursion'):
            _logger.info("WSEM Existe orden.")
            self = self.with_context(avoid_recursion=True)
            DiscountMixin.update_discount_lines(self.order_id,None,'in')
            
        return result               

class InvoiceLineCustom(models.Model):
    _inherit = 'account.move.line'
    discount_id = fields.Many2one('res.partner.discount', string='Discount ID')

    def create(self, vals_list):
        _logger.info(f'WSEM Descuentos factura ini')
        lines = super(InvoiceLineCustom, self).create(vals_list)
        for line in lines:
            _logger.info(f'WSEM Descuentos factura. move {line.move_id.id}')
            if line.move_id and not line._context.get('avoid_recursion'):
                line = line.with_context(avoid_recursion=True)
                DiscountMixin.update_discount_lines(line.move_id, line,line.move_id.move_type)
        return lines

    def write(self, values):       
        result = super(InvoiceLineCustom, self).write(values)
        _logger.info(f'WSEM Descuentos previo itera')
        for record in self:
            _logger.info(f'WSEM Descuentos Factura Write en factura {record.move_id.id}')
            if record.move_id and not record._context.get('avoid_recursion'):
                _logger.info("WSEM Existe factura.")
                record = record.with_context(avoid_recursion=True)
                DiscountMixin.update_discount_lines(record.move_id, None,record.move_id.move_type)
        return result

class DiscountMixin:

#DESCUENTOS GLOBALES  
    @staticmethod                  
    def ws_is_desc(line):
        return line.product_id and line.product_id.name == 'DESCUENTO' 

    @staticmethod                  
    def is_line_real_or_virtual(line):
        # Verificar si el id es un entero, lo que indica un registro guardado
        if isinstance(line.id, int):
            return "real"
        # Verificar si el id es una instancia de NewId para registros no guardados
        elif isinstance(line.id, models.NewId):
            id_str = str(line.id)
            # Verificar si contiene la palabra "virtual" en la representación de cadena
            if "virtual" in id_str:
                return "virtual"
            else:
                return "newid"
        # Por defecto, considerar cualquier otro caso como desconocido
        else:
            return "unknown"
            
    @staticmethod 
    def update_discount_lines(order, discount_line, move_type):
        # Si ya existe la bandera, salimos inmediatamente
        if order.env.context.get('avoid_recursion'):
            return

		# Activamos la bandera en el contexto antes de seguir
        order = order.with_context(avoid_recursion=True)       

        if hasattr(order, 'order_line'):
            lines = order.order_line
        elif hasattr(order, 'invoice_line_ids'):
            lines = order.invoice_line_ids
        else:
            _logger.warning(f'WSEM No se pudo determinar las líneas del objeto {order}')
            return

        sorted_lines = lines.sorted(key=lambda l: l.sequence)


        base_before_discount = 0.0
        discount_line_updated = False

        for line in sorted_lines:            
            # Si es una línea de descuento, calcular el descuento y actualizarla
            es_real=DiscountMixin.is_line_real_or_virtual(line)=='real'
            _logger.info(f'WSEM itera linea id:{line.id}, name:{line.product_id.name}, base:{base_before_discount}, seq:{line.sequence}. Es real {es_real} size lineas {len(sorted_lines)}')
                        
            if es_real:
                _logger.info(f'WSEM si es real pro name: {line.product_id.name}')
                updated=DiscountMixin.update_discount_line(line, base_before_discount,move_type)
                
                if updated and discount_line and line == discount_line:
                    discount_line_updated = True
                            
                # Actualizar la base antes de descuento acumulada
                # Notar que si la linea anterior era descuento, debe haberse actualizado price_subtotal en el write de cuando fue modificada, 
                # ahora se actualiza de nuevo el descuento pero no afecta al calculo del subtotal que debe tenerlo previamente reflejado
                #actualizo el subototal de la linea aplicando el descuento
                subtotal_linea=line.price_subtotal
                base_before_discount += subtotal_linea
                
        # Si la línea de descuento no se actualizó en sorted_lines, forzar su actualización
        if discount_line and not discount_line_updated:
            _logger.info(f'WSEM forzando discount line {discount_line.product_id.name}')
            DiscountMixin.update_discount_line(discount_line, base_before_discount,move_type)
                
    @staticmethod
    def update_discount_line(line, base_before_discount, move_type):
        if line.product_id.name == 'DESCUENTO':
            if line.name:
                signo = 1 if move_type in ['out_refund'] else -1
                discount_percentage = DiscountMixin.extract_discount_percentage(line.name)
                _logger.info(f'WSEM descuento Porc {discount_percentage} type {move_type} signo {signo} doc {line.move_id.name}')
                if discount_percentage:
                    precio_lin_desc = signo * (base_before_discount * (discount_percentage / 100.0))
                    
                    # Valores actuales
                    current_price_unit = line.price_unit
                    current_qty = line.product_uom_qty if 'product_uom_qty' in line._fields else None
                    
                    # Valores propuestos
                    values_to_update = {'price_unit': precio_lin_desc}
                    if 'product_uom_qty' in line._fields:
                        values_to_update['product_uom_qty'] = 1
                    
                    # Comprobar si hay cambios reales
                    need_write = False
                    if current_price_unit != values_to_update['price_unit']:
                        need_write = True
                    if 'product_uom_qty' in values_to_update and current_qty != values_to_update['product_uom_qty']:
                        need_write = True
                    
                    if need_write:
                        _logger.info(f'WSEM need write')
                        line.write(values_to_update)
                    else:
                        _logger.info(f'WSEM No need write')
                    
                    return True
        return False

     
    @staticmethod      
    def extract_discount_percentage(description):
        # Extraer el porcentaje de descuento de la descripción, esperando la sintaxis "DESCUENTO X%"
        match = re.search(r'^(?:\D+\s+)*(\d+(?:\.\d+)?)%\s*(?:\w+\s*)*', description)
        if match:
            return float(match.group(1))
        return None
        
    def _apply_discounts(record):
        discount_product = record.env['product.product'].search([('name', '=', 'DESCUENTO')], limit=1) # Asumiendo que tienes un producto llamado 'Descuento'
        if not discount_product:
            _logger.info(f'WSEM no hay descuentos')
            return  # No hacer nada si el producto no existe

        lines = None
        line_model = None
        partner_id = None
        move_type = None

        if hasattr(record, 'order_line'):
            _logger.info(f'WSEM es clase pedido')
            lines = record.order_line
            line_model = record.env['sale.order.line']
            partner_id = record.partner_id.id

        elif hasattr(record, 'invoice_line_ids'):
            lines = record.invoice_line_ids
            line_model = record.env['account.move.line']
            partner_id = record.partner_id.id
            move_type = record.move_type
            if move_type not in ['out_invoice', 'out_refund']:
                _logger.info("Skipping record as move_type is not 'out_invoice' or 'out_refund'")
                return

        if lines and partner_id > 0:
            _logger.info(f'WSEM hay partner')
            discounts = record.env['res.partner.discount'].search([('partner_id', '=', partner_id)])
            if not discounts:
                _logger.info(f'WSEM not hay descuentos partner')
                return  # Si no hay descuentos, saltar al siguiente registro

            # Obtener la secuencia más alta de las líneas existentes
            max_sequence = max(lines.mapped('sequence'), default=0)

            
            # Crear nuevas líneas de descuento
            for discount in discounts:
                
                existing_line = lines.filtered(lambda l: l.discount_id.id == discount.id)
                _logger.info(f'WSEM itera descuentos {existing_line} cond {bool(existing_line)}')
                if not existing_line:
                    _logger.info(f'WSEM creando linea')
                    max_sequence += 1
                    line_model.create({
                        'order_id' if hasattr(record, 'order_line') else 'move_id': record.id,
                        'product_id': discount_product.id,
                        'name': f"{discount.name} {discount.discount_percent}%",
                        'discount_id': discount.id,
                        'price_unit': 0.0,
                        'product_uom_qty' if hasattr(record, 'order_line') else 'quantity': 1,
                        'sequence': max_sequence,
                        
                    })
            DiscountMixin.update_discount_lines(record,None,move_type)

