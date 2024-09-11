from odoo import api, fields, models
from odoo.exceptions import UserError

from collections import defaultdict
from datetime import timedelta
import math
import logging
_logger = logging.getLogger(__name__)

class MrpDateGrouping(models.TransientModel):
    _name = 'mrp.date.grouping'
    _description = 'Plan Production'

    daysgroup = fields.Integer(string='Agrupar cada produccion en dias', default=100, required=True)
    ngroups = fields.Integer(string='Numero de grupos a planificar', default=1000, required=True)

    def mrp_planning(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids'))
        sale_orders = sorted(sale_orders, key=lambda r: (
            r.commitment_date.date() if r.commitment_date else r.create_date.date(),
            r.tag_ids[0].name if r.tag_ids else ''
        ))

        current_group = []
        products_demand = {}  # key product objeto
        product_packaging = {}  # Nuevo diccionario para almacenar el envasado
        
        start_dates = {}  # key producto valor fecha
        start_gr_date = None
        group_end_date = None
            
        end_dates = defaultdict(lambda: fields.Datetime.now())  # key product.id int
        planned_groups = 0
        current_tag = None
        self.find_max_reserved_date_for_work_centers(sale_orders, start_dates, fields.Datetime.now())
        
        _logger.info("WSEM Inicio:")
        for index, order in enumerate(sale_orders):
            es_ultima_iteracion = (index == len(sale_orders) - 1)
            _logger.info(f"WSEM itera order indice {index} numero ordenes {len(sale_orders)} es ultima {es_ultima_iteracion}")
            order_tag = order.tag_ids[0].name if order.tag_ids else ""
            
            if current_tag != order_tag or \
               group_end_date and group_end_date >= start_gr_date + timedelta(days=self.daysgroup) or \
               es_ultima_iteracion:              
                                
                _logger.info(f"WSEM fin de grupo, start_date:{start_gr_date.strftime('%Y-%m-%d %H:%M:%S') if start_gr_date else 'N/A'}, fecha grupo: {group_end_date.strftime('%Y-%m-%d %H:%M:%S') if group_end_date else 'N/A'}, order tag: {order_tag}, diferente: {current_tag != order_tag}")

                planned_groups += 1
                self._create_production_orders(products_demand, product_tags, start_dates, end_dates, product_packaging)

                if planned_groups > self.ngroups:
                    _logger.info("WSEM superado n grupos")
                    break

                current_group = []
                current_tag = None
                start_gr_date = None
                group_end_date = None                                  
                self.find_max_reserved_date_for_work_centers(sale_orders, start_dates, fields.Datetime.now())            
        
            if current_tag is None or current_tag == order_tag:
                current_tag = order_tag                       
                current_group.append(order)
                _logger.info(f"WSEM itera orden : {order.name} n-ordenes:{len(current_group)} order tag:{current_tag}")
                                                                                                                        
                products_demand, product_tags, product_packaging = self._products_demand(current_group)
                
                self._calculate_lead_times_by_phase(products_demand, start_dates, end_dates)
                order.expected_date = self.max_reserved_date_for_order(order, end_dates)
                
                start_gr_date = min(start_dates.values())
                group_end_date = max(end_dates.values())
                
                _logger.info(f"WSEM fecha grupo : {group_end_date.strftime('%Y-%m-%d %H:%M:%S')}")
            
            
    def max_reserved_date_for_order(self, orden, end_dates):

        fecha_maxima = False
        
        for linea in orden.order_line:            
            # Crear la clave como una tupla (name, product_id, product_packaging_id)
            productkey = (linea.name, linea.product_id, linea.product_packaging_id)
            if end_dates[productkey]:
                start_date = end_dates.get(productkey, fields.Datetime.now())
                if not fecha_maxima or start_date > fecha_maxima:
                    fecha_maxima = start_date        
        return fecha_maxima or fields.Datetime.now()
        

    def find_max_reserved_date_for_work_centers(self, ordenes_venta, start_dates, default_max_date):        

        for orden in ordenes_venta:
            for linea in orden.order_line:                
                productkey = (linea.name, linea.product_id, linea.product_packaging_id)
                bom = self.env['mrp.bom']._bom_find(linea.product_id)[linea.product_id]

                # Continuar solo si el producto tiene un BOM y el BOM tiene operaciones
                if bom and bom.operation_ids:
                    work_centers = bom.operation_ids.mapped('workcenter_id')
                    max_date = fields.Datetime.now()

                    for wc in work_centers:
                        # Encuentra todas las órdenes de trabajo para este centro
                        work_orders = self.env['mrp.workorder'].search([
                            ('workcenter_id', '=', wc.id),
                            ('state', 'not in', ['done', 'cancel'])  # Ejemplo de filtro por estado
                        ])
                        
                        # Obtén la fecha de finalización más reciente de las órdenes de trabajo
                        if work_orders:                            
                            wc_max_date = max(work_orders.mapped(lambda wo: wo.date_planned_finished or default_max_date))
                            if wc_max_date and wc_max_date > max_date:
                                max_date = wc_max_date

                    # Actualizar la fecha máxima para el producto
                    if productkey not in start_dates or max_date > start_dates[productkey]:
                        start_dates[productkey] = max_date

    def _calculate_lead_times_by_phase(self, products_demand, start_dates, end_dates):
        
        workcenter_sched = defaultdict(lambda: fields.Datetime.now()) #key workcenter id valor el tiempo para producir teniendo en cuenta capacidad en paralelo
        workcenter_of_products = {}
        
        #calcular fechas de finalizacion por centro de trabajo, y la fecha start es la final del mismo centro para la fase anterior        

        for productkey in products_demand:
            #start basado en ordenes existentes o bacth anteriores, antes de ejecutarse por primera vez este batch
            pro_name, product, packaging = productkey
            start_date_init = start_dates.get(productkey, fields.Datetime.now())
            #tiempo total en que se liberara el centro de este producto en esta planificacion
            lead_time_wc_reservado = self._get_leadtime(workcenter_sched, workcenter_of_products, product)
            
            self._calculate_product_lead_time(productkey, workcenter_sched, workcenter_of_products, products_demand)
            new_lead_time = self._get_leadtime(workcenter_sched, workcenter_of_products, product)
            incr_lead_time = new_lead_time - lead_time_wc_reservado
            start_dates[productkey] = start_date_init + timedelta(days=lead_time_wc_reservado/1440.0)
            _logger.info(f"WSEM start dates producto {pro_name} start {start_dates[productkey].strftime('%Y-%m-%d %H:%M:%S')} incr lead {incr_lead_time}")
             
            end_date = start_dates[productkey] + timedelta(days=incr_lead_time/1440.0)
            end_dates[productkey] = end_date                    
                    
        return end_dates

    def _get_leadtime(self, workcenter_sched, workcenter_of_products, product):
        wid = workcenter_of_products.get(product, 0)
        if wid == 0:
            return 0
        return workcenter_sched.get(wid, 0)
 
    def _products_demand(self, sale_orders):
        products_demand = {}
        product_tags = {}
        product_packaging = {}  # Nuevo diccionario para almacenar el envasado
        
        for order in sale_orders:
            for line in order.order_line:
                productkey = (line.name, line.product_id, line.product_packaging_id)             
                
                                                 
                if productkey in products_demand:
                    _logger.info(f"WSEM Clave encontrada: {productkey}, demanda previa: {products_demand[productkey]}")
                else:
                    _logger.info(f"WSEM Clave nueva: {productkey}")

                                                                                                           
                prev_demand = products_demand.get(productkey, 0)
                products_demand[productkey] = prev_demand + line.product_uom_qty 

                                            
                _logger.info(f"Actualizado products_demand[{productkey}] = {products_demand[productkey]}")                                                    
                
                tag_arr = order.tag_ids.filtered(lambda t: t.name.strip())
                tag = ''
                if tag_arr:
                    tag = tag_arr[0].name.strip()
                product_tags[productkey] = tag 
                                                                                 
                                                                                                                                                                                          

                # Capturar el envasado del pedido
                                             
                product_packaging[productkey] = line.product_packaging_id.id if line.product_packaging_id else False

                self._products_demand_bomlines(products_demand, productkey, product_tags, tag, line.product_uom_qty)                                                                         
                                      

        return products_demand, product_tags, product_packaging

    def _products_demand_bomlines(self, products_demand, productkey, product_tags, tag, root_quantity, visited=None):
        pro_name, product, packaging = productkey

        # Inicializar el conjunto de productos visitados si no se ha hecho
        if visited is None:
            visited = set()

        # Verificar si el producto ya ha sido visitado
        if product in visited:
            raise UserError(f"Recursividad detectada: el producto {product.display_name} se encuentra a sí mismo en su BOM.")

        # Añadir el producto actual al conjunto de visitados
        visited.add(product)

        try:
            # Encontrar el BOM asociado al producto
            bom_dict = self.env['mrp.bom']._bom_find(product)

            # Verificar que el BOM se encontró y contiene el producto como clave
            if not bom_dict or product not in bom_dict:
                return  # Salir si no se encuentra el BOM correcto

            # Obtener el BOM específico del producto
            bom = bom_dict[product]

            user_language = self.env.user.lang

            # Iterar sobre las líneas del BOM para calcular la demanda
            for line in bom.bom_line_ids:
                linname = self._generate_default_name(line.product_id, user_language)
                sub_productkey = (linname, line.product_id, None)  # None para el packaging de componentes

                # Actualizar la cantidad demandada del subproducto
                if sub_productkey not in products_demand:
                    products_demand[sub_productkey] = 0

                products_demand[sub_productkey] += root_quantity * line.product_qty

                # Asignar la etiqueta al subproducto si no está ya asignada
                if sub_productkey not in product_tags:
                    product_tags[sub_productkey] = tag

                # Llamada recursiva para procesar subproductos
                self._products_demand_bomlines(products_demand, sub_productkey, product_tags, tag, root_quantity * line.product_qty, visited)
        finally:
            # Eliminar el producto del conjunto de visitados al salir de la recursión
            visited.remove(product)


    def _get_bom_phases(self, bom):
        phases = set()
        for bom_line in bom.bom_line_ids:            
            child_bom = self.env['mrp.bom']._bom_find(bom_line.product_id)[bom_line.product_id]
            if child_bom:
                phases.update(self._get_bom_phases(child_bom))
            else:
                phases.add(0)

        if not phases:
            return {0}
        else:
            return {phase + 1 for phase in phases}

    def _calculate_product_lead_time(self, productkey, workcenter_sched, workcenter_of_products, products_demand):
        
        proname, product, packaging = productkey
        bom = self.env['mrp.bom']._bom_find(product)[product]
        user_language = self.env.user.lang
        
        if bom:
            for operation in bom.operation_ids:
                workcenter = operation.workcenter_id
                cycle_time = operation.time_cycle
                
                if productkey not in products_demand:
                    _logger.info(f"WSEM error falta:{proname}") 
                workcenter_sched[workcenter.id] = workcenter_sched.get(workcenter.id, 0.0) + products_demand[productkey] * cycle_time / workcenter.default_capacity       
                workcenter_of_products[product] = workcenter.id
                _logger.info(f"WSEM cycle t:{cycle_time} leadtime:{workcenter_sched[workcenter.id]}")               

            for line in bom.bom_line_ids:
                linname = self._generate_default_name(line.product_id, user_language)
                sub_productkey = (linname, line.product_id, None)  # None para el packaging de componentes
                self._calculate_product_lead_time(sub_productkey, workcenter_sched, workcenter_of_products, products_demand)
                _logger.info("WSEM añadido extra")

    def _create_production_orders(self, products_demand, product_tags, start_dates, end_dates, product_packaging):
        """
        Crear órdenes de producción basadas en los productos agrupados por fase,
        considerando las cantidades acumuladas de cada producto.
        
        Nota, no sirve asignar fecha fin a la produccion porque lo recalcula a partir de sus ordenes de trabajo, ademas tiene en cuenta horarios
        Sin ambargo en ORM solo recalcula fecha fin de la produccion si sus ordenes de trabajo no tienen fecha de inicio, si la tienen no hace nada, 
        por tanto es necesario hacerlo en dos pasos, primero asigno fecha de inicio a las ordenes de trabajo y despues fecha de fin a la produccion
        """
            
        ProductionOrder = self.env['mrp.production']
        
        for productkey, quantity in products_demand.items():
            proname, product, packaging = productkey
            _logger.info(f"WSEM crea ordenes itera {proname} qty:{quantity}")
            bom = self.env['mrp.bom']._bom_find(product)[product]
            if not bom:
                _logger.info(f"WSEM No se encontró BOM para el producto {product.display_name}. Se omite la creación de la orden de producción.")
                #crear ordenes de compra
                self._create_reorder_rule(product,quantity)
                continue
            end_date_pro=end_dates[productkey]
            start_date_pro=start_dates[productkey]
            multiplos=math.ceil(quantity / bom.product_qty)
            # Preparar datos para la creación de la orden de producción            
            production_data = {
                'product_id': product.id,
                'product_qty': multiplos*bom.product_qty,
                'bom_id': bom.id,
                'ws_multiplos':multiplos,
                'date_planned_start': start_date_pro,
                'company_id': self.env.company.id,  # Asume que la compañía se toma del contexto actual
            }

             # Agregar la etiqueta como origen si se encontró para el producto
            if productkey in product_tags:
                production_data['origin'] = product_tags[productkey]                                                                                                                                                                                     
            # Opcional: establecer el usuario si está disponible en el contexto/env
            
            # Agregar el envasado a la orden de producción
            if productkey in product_packaging:
                production_data['wsem_packaging_id'] = product_packaging[productkey]                                    
            if self.env.user and self.env.user.id:
                production_data['user_id'] = self.env.user.id

            # Crear la orden de producción
            production_order = ProductionOrder.create(production_data)
            
            max_work_order_finish_date = None  # Inicializa la variable para almacenar la fecha de finalización más reciente
            
            # Actualizar las fechas de las órdenes de trabajo y calcular la fecha de finalización más reciente
            for work_order in production_order.workorder_ids:
                work_order.date_planned_start = start_date_pro                
                
                if not max_work_order_finish_date or work_order.date_planned_finished > max_work_order_finish_date:
                    max_work_order_finish_date = work_order.date_planned_finished

            # Si se encontró alguna fecha de finalización más reciente, actualiza la orden de producción
            if max_work_order_finish_date:
                production_order.date_planned_finished = max_work_order_finish_date
            else:
                # Si no hay órdenes de trabajo o ninguna tiene fecha de finalización, usa end_date_pro
                production_order.date_planned_finished = end_date_pro
                                    

            _logger.info(f"WSEM Orden de producción creada: {production_order.name} para el producto {product.display_name} con cantidad {quantity}.")

        _logger.info("WSEM  Todas las órdenes de producción han sido creadas.")


    def _create_reorder_rule(self, product, reorder_qty):
        # Obtener el almacén principal
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)

        # Obtener la ubicación de stock del almacén
        location = warehouse.lot_stock_id

        # Obtener la ruta de compra desde el identificador externo
        buy_route = self.env.ref('purchase_stock.route_warehouse0_buy')
        manufacture_route = self.env.ref('mrp.route_warehouse0_manufacture')

        # Obtener el producto para el cual se creará la regla de reabastecimiento

        # Verificar si el producto tiene una ruta de compra
        if buy_route in product.route_ids or manufacture_route in product.route_ids:
            # Verificar si ya existe una regla de reabastecimiento para el producto
            existing_rule = self.env['stock.warehouse.orderpoint'].search([
                ('product_id', '=', product.id),
                ('location_id', '=', location.id),
            ], limit=1)

            if existing_rule:
                # Si la ruta de fabricación está activa, actualizar específicamente qty_to_order
                if manufacture_route in product.route_ids:
                    existing_rule.qty_to_order = reorder_qty
                    existing_rule.save()
                    '''else:
                    # Actualizar la regla existente para otros casos
                    #existing_rule.write({
                    #    'product_max_qty': reorder_qty,  # Actualizar la cantidad máxima de stock
                    #})'''
            else:
                # Crear la regla de reabastecimiento
                reorder_rule = self.env['stock.warehouse.orderpoint'].create({
                    'name': 'Regla de reabastecimiento para ' + product.name,
                    'product_id': product.id,
                    'product_min_qty': 1,  # Cantidad mínima de stock
                    'product_max_qty': reorder_qty,  # Cantidad máxima de stock
                    'qty_multiple': 1,  # Cantidad múltiple para el reabastecimiento
                    'trigger': 'manual',  # Disparador automático cuando el stock esté por debajo del mínimo
                    'location_id': location.id,
                    'warehouse_id': warehouse.id,
                    'company_id': self.env.company.id,
                    'route_id': buy_route.id,  # Ruta de compra
                })

        return True
 
    def _generate_default_name(self, product, language):
        default_code = product.default_code or ''
        name_idioma = product.with_context(lang=language).name or product.name
        dn= f"[{default_code}] {name_idioma}"
        
        return dn