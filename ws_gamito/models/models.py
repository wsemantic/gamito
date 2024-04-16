import logging, re
from odoo import models, fields, api
from datetime import datetime
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


class DocOrderGamitoMixing(models.AbstractModel):
    _name = 'doc.order.gamito.mixin'
    _description = 'Logica comun compra venta descuentos Mixin'
#MRP
    '''
    def calcular_fecha_entrega(self):
        # Ordena los pedidos por fecha de entrega de forma ascendente
        orders = self.sorted(key=lambda r: r.date_order)
        # Define la variable temporal fecha_entrega
        fecha_entrega = fields.Date.today()  # o usar la fecha mínima de los pedidos seleccionados

        for order in orders:
            acumulado_tiempo = 0.0
            for line in order.order_line:
                product = line.product_id
                # Considera solo los productos que tienen lista de materiales
                if product.bom_ids:
                    bom = product.bom_ids[0]  # Asume que se toma la primera lista de materiales
                    tiempo, fecha_entrega = self._calcular_tiempo_acumulado(bom, fecha_entrega, acumulado_tiempo)
                    acumulado_tiempo += tiempo
            
            # Actualiza la fecha estimada de entrega del pedido
            order.write({'fecha_estimada_entrega': fecha_entrega})

    def _calcular_tiempo_acumulado(self, bom, fecha_entrega, acumulado_tiempo):
        # Itera a través de las operaciones de la lista de materiales
        tiempos = []
        for operation in bom.operation_ids:
            centro_trabajo = operation.workcenter_id
            tiempo_operacion = operation.time_cycle * centro_trabajo.capacity  # ajustar según la lógica de capacidad
            tiempos.append(tiempo_operacion)
            # Si la lista de materiales tiene productos intermedios, recursivamente calcula el tiempo
            for line in bom.bom_line_ids:
                if line.product_id.bom_ids:
                    sub_bom = line.product_id.bom_ids[0]
                    _, fecha_entrega = self._calcular_tiempo_acumulado(sub_bom, fecha_entrega, acumulado_tiempo + max(tiempos))
        
        # Considera las operaciones en paralelo, tomando el tiempo más largo
        tiempo_maximo = max(tiempos) if tiempos else 0
        acumulado_tiempo += tiempo_maximo

        # Verifica si se supera un día de trabajo
        if acumulado_tiempo > 24:  # Asumiendo 24 horas como duración de un día laboral
            fecha_entrega += timedelta(days=1)
            acumulado_tiempo -= 24  # Restablece el acumulado para el siguiente día

        return acumulado_tiempo, fecha_entrega'''

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

#DESCUENTOS GLOBALES                    
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
    
    def _update_discount_lines(self):
        # Ordenar las líneas por secuencia u otro criterio apropiado
        sorted_lines = self.order_line.sorted(key=lambda l: l.sequence)


        base_before_discount = 0.0
        fields_dict = self._fields

        for line in sorted_lines:            
            # Si es una línea de descuento, calcular el descuento y actualizarla
            _logger.info(f'WSEM itera linea id:{line.id}, name:{line.product_id.name}, base:{base_before_discount}, seq:{line.sequence}')
            subtotal_linea=line.price_subtotal            
            if SaleOrder.is_line_real_or_virtual(line):
                if line.product_id.name == 'DESCUENTO':                
                    if line.name:                        
                        discount_percentage = line._extract_discount_percentage(line.name)                                
                        if discount_percentage:                                            
                            line.product_uom_qty= 1
                            precio_lin_desc=-(base_before_discount * (discount_percentage / 100.0))
                            line.price_unit= precio_lin_desc
                            subtotal_linea= precio_lin_desc
                            _logger.info(f'WSEM descuento:{subtotal_linea}')
                            
                # Actualizar la base antes de descuento acumulada
                base_before_discount += subtotal_linea
            
class SaleOrder(models.Model):
    _inherit = ['sale.order','doc.order.gamito.mixin']

class PurchaseOrder(models.Model):
    _inherit = ['purchase.order','doc.order.gamito.mixin']

class DocOrderLineGamitoMixin(models.AbstractModel):
    _name = 'doc.order.line.gamito.mixin'
    _description = 'Logica comun compra venta descuentos Mixin'
    
    #api.onchange('product_uom_qty', 'price_unit', 'product_id', 'tax_id', 'name','sequence')
    def _update_discount_lines(self):
        if self.order_id and not self._context.get('avoid_recursion'):
            self = self.with_context(avoid_recursion=True)
            #al llamar al bucle de la orden _update_discount_lines, se va ejecutar el update de todas las lineas, sin comprobar contexto, 
            # cada update de cada linea pasara aqui de nuevo recursivamente, esta vez cortando el bucle por el conexto
            self.order_id._update_discount_lines()            
            
    def _extract_discount_percentage(self, description):
        # Extraer el porcentaje de descuento de la descripción, esperando la sintaxis "DESCUENTO X%"
        match = re.search(r'^(?:DESCUENTO\s+)?(\d+(?:\.\d+)?)%', description)
        if match:
            return float(match.group(1))
        return None
        
    def write(self, values):       
        # Llama al método super() para ejecutar la lógica original de write
        result = super(SaleOrderLine, self).write(values)

        # Lógica personalizada después de la actualización
        _logger.info("WSEM Logica personalizada después de actualizar las líneas del pedido.")
        self._update_discount_lines();
        return result

class SaleOrderLine(models.Model):
    _inherit = ['sale.order.line','doc.order.line.gamito.mixin']
    
class PurchaseOrderLine(models.Model):
    _inherit = ['purchase.order.line','doc.order.line.gamito.mixin']
    
#from odoo import models, fields, api
#from datetime import datetime
class StockLot(models.Model):
    _inherit = 'stock.lot'

    @api.model_create_multi
    def create(self, val_list):
        for vals in val_list:
            product_id = vals.get('product_id', False)
            if product_id:
                product = self.env['product.product'].browse(product_id)
                # Verificar si el producto tiene una ruta de fabricación
                manufacture_route = self.env.ref('mrp.route_warehouse0_manufacture')  # Asegúrate de que este es el ID correcto de la ruta de fabricación en tu base de datos
                if manufacture_route in product.route_ids:
                    # Generar el nombre del lote usando la referencia del producto y la fecha actual
                    date_now = datetime.now()
                    formatted_date = date_now.strftime("%y%W%w")
                    product_ref = product.default_code or 'NO_REF'
                    new_lot_name = f"{product_ref}-{formatted_date}"

                    # Buscar un lote existente con el mismo nombre
                    existing_lot = self.env['stock.lot'].search([('name', '=', new_lot_name), ('product_id', '=', product_id)], limit=1)
                    if existing_lot:
                        # Si existe, usar el lote existente
                        _logger.info(f'WSEM ya existía el lote :{new_lot_name}')
                        return existing_lot
                    else:
                        # Si no existe, asignar el nuevo nombre y continuar con la creación
                        _logger.info(f'WSEM creando lote :{new_lot_name}')
                        vals['name'] = new_lot_name
        return super(StockLot, self).create(val_list)
                

#removal estrategia least_fifo
class StockQuantCustom(models.Model):
    _inherit = 'stock.quant'
    en_consumo_desde = fields.Datetime(
        'En consumo desde',
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