from odoo import api, fields, models
from collections import defaultdict
from datetime import timedelta
import logging
_logger = logging.getLogger(__name__)

class MrpDateGrouping(models.TransientModel):
    _name = 'mrp.date.grouping'
    _description = 'Plan Production'

    daysgroup = fields.Integer(string='Number of Days to Group', default=7, required=True)
    ngroups = fields.Integer(string='Number of Groups to Plan', default=2, required=True)

    def mrp_planning(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids'))
        sale_orders = sale_orders.sorted(key=lambda r: r.commitment_date if r.commitment_date else r.create_date)

        current_group = []
        
        start_dates={}
        self.find_max_reserved_date_for_work_centers(sale_orders,start_dates)
        end_dates=defaultdict(lambda: fields.Datetime.now())
        planned_groups=0
        
        _logger.info("WSEM Inicio:")
        for index, order in enumerate(sale_orders):
            es_ultima_iteracion = (index == len(sale_orders) - 1)
            current_group.append(order)
            _logger.info(f"WSEM itera orden : {order.name} n-ordenes:{len(current_group)}")
            #products_demand se redefine actualizado con cada nueva orden
            products_demand = self._products_demand(current_group)
            
            self._calculate_lead_times_by_phase(products_demand, start_dates,end_dates)
            order.commitment_date = self.max_reserved_date_for_order(order, end_dates)
            
            start_gr_date= min(start_dates.values())
            group_end_date = max(end_dates.values())
            
            _logger.info(f"WSEM fecha grupo : {group_end_date.strftime('%Y-%m-%d %H:%M:%S')}")

            if group_end_date >= start_gr_date + timedelta(days=self.daysgroup) or es_ultima_iteracion:
                #TODO partir ordenes si se pasa de fecha
                #if group_end_date >= start_gr_date and not len(current_group) == 1:
                #    _logger.info("WSEM superada fecha grupo")
                #    # Elimino grupo que se pasa y actualizo datos
                #    current_group.pop()
                #    products_demand = self._products_demand(current_group)
                #    start_dates, end_dates = self._calculate_lead_times_by_phase(products_demand, start_dates)
                #    group_end_date = max(end_dates.values())
                #else:
                #    _logger.info("WSEM fin de grupo ")                
                _logger.info("WSEM fin de grupo ")                
                planned_groups++
                self._create_production_orders(products_demand, start_dates, end_dates)

                if planned_groups > self.ngroups:
                    _logger.info("WSEM superado n grupos")
                    break

                current_group = []
                self.find_max_reserved_date_for_work_centers(sale_orders,start_dates)
            
            
    def max_reserved_date_for_order(self, orden, end_dates):

        fecha_maxima = False
        
        for linea in orden.order_line:
            product = linea.product_id
            if end_dates[product.id]:
                start_date=end_dates.get(product.id, fields.Datetime.now())
                if not fecha_maxima or start_date > fecha_maxima:
                    fecha_maxima = start_date        
        return fecha_maxima or fields.Datetime.now()
        

    def find_max_reserved_date_for_work_centers(self, ordenes_venta,start_dates):        

        for orden in ordenes_venta:
            for linea in orden.order_line:
                product = linea.product_id
                bom = self.env['mrp.bom']._bom_find(product)[product]

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
                            wc_max_date = max(work_orders.mapped('date_planned_finished'))
                            if wc_max_date and wc_max_date > max_date:
                                max_date = wc_max_date

                    # Actualizar la fecha máxima para el producto
                    if product.id not in start_dates or max_date > start_dates[product.id]:
                        start_dates[product.id] = max_date

    def _calculate_lead_times_by_phase(self, products_demand, start_dates, end_dates):
        
        workcenter_sched=defaultdict(lambda: fields.Datetime.now())
        workcenter_of_products={}
        
        #calcular fechas de finalziacion por centro de trabajo, y la fecha start es la final del mismo centro para la fase anterior        

        for product in products_demand:
            #start basado en ordenes existentes o bacth anteriores, antes de ejecutarse por primera vez este batch
            start_date_init=start_dates.get(product.id, fields.Datetime.now())
            #tiempo total en que se liberara el centro de este producto en esta planificacion
            lead_time_wc_reservado= self._get_leadtime( workcenter_sched, workcenter_of_products, product )
            
            self._calculate_product_lead_time(product,workcenter_sched,workcenter_of_products,products_demand)
            new_lead_time= self._get_leadtime( workcenter_sched, workcenter_of_products, product )
            incr_lead_time=new_lead_time-lead_time_wc_reservado
            start_dates[product.id] = start_date_init + timedelta(days=lead_time_wc_reservado/1440.0)
            _logger.info(f"WSEM start dates producto {product.name} start {start_dates[product.id].strftime('%Y-%m-%d %H:%M:%S')} incr lead {incr_lead_time}" )
             
            end_date = start_dates[product.id] + timedelta(days=incr_lead_time/1440.0)
            end_dates[product.id] = end_date                    
                    
        else:
            _logger.info(f"WSEM no hay fases" )

        return end_dates

    def _get_leadtime(self, workcenter_sched, workcenter_of_products, product ):
        wid=workcenter_of_products.get(product.id,0)
        if wid==0:
            return 0
        return workcenter_sched.get(wid,0)
 
    def _products_demand(self, sale_orders):
        products_demand = {}

        for order in sale_orders:
            for line in order.order_line:
                product = line.product_id
                bom = self.env['mrp.bom']._bom_find(product)[product]                                                                                                                                                                                                                                          
                                                         
                products_demand[product] = products_demand.get(product,0)+line.product_uom_qty

        return products_demand

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

    def _calculate_product_lead_time(self, product,workcenter_sched,workcenter_of_products,products_demand):
        
        bom = self.env['mrp.bom']._bom_find(product)[product]
        
        if bom:
            for operation in bom.operation_ids:
                workcenter = operation.workcenter_id
                cycle_time = sum(wc_line.time_cycle for wc_line in workcenter.routing_line_ids)
                workcenter_sched[workcenter.id]=workcenter_sched.get(workcenter.id,0.0)+products_demand[product]*cycle_time / workcenter.default_capacity       
                workcenter_of_products[product.id]=workcenter.id
                _logger.info(f"WSEM cycle t:{cycle_time} leadtime:{workcenter_sched[workcenter.id]}")               

            for line in bom.bom_line_ids:
                self._calculate_product_lead_time(line.product_id,workcenter_sched,workcenter_of_products,products_demand)
                _logger.info("WSEM añadido extra")

    def _create_production_orders(self, products_demand, start_dates, end_dates):
        """
        Crear órdenes de producción basadas en los productos agrupados por fase,
        considerando las cantidades acumuladas de cada producto.
        """
            
        ProductionOrder = self.env['mrp.production']
        
        for product, quantity in products_demand.items():
            bom = self.env['mrp.bom']._bom_find(product)[product]
            if not bom:
                _logger.info(f"WSEM No se encontró BOM para el producto {product.display_name}. Se omite la creación de la orden de producción.")
                continue
            end_date_pro=end_dates[product.id]
            start_date_pro=start_dates[product.id]
            # Preparar datos para la creación de la orden de producción            
            production_data = {
                'product_id': product.id,
                'product_qty': quantity,
                'bom_id': bom.id,
                'date_planned_start': start_date_pro,
                'company_id': self.env.company.id,  # Asume que la compañía se toma del contexto actual
            }

            # Opcional: establecer el usuario si está disponible en el contexto/env
            if self.env.user and self.env.user.id:
                production_data['user_id'] = self.env.user.id

            # Crear la orden de producción
            production_order = ProductionOrder.create(production_data)
            
            # Actualizar las fechas de las órdenes de trabajo
            work_orders = production_order.workorder_ids
            for work_order in work_orders:
                work_order.date_planned_start = start_date_pro  
            
            #date_planned_finished se recalcula al asignar la fecha de las ordenes de trabajo, o a la fecha de start si no existe. Pero desde ORM solo se actualiza si era nula, aunque asigne fecha de wo, tengo que actualizar aqui
            production_order.date_planned_finished=end_date_pro

            _logger.info(f"WSEM Orden de producción creada: {production_order.name} para el producto {product.display_name} con cantidad {quantity}.")

        _logger.info("WSEM  Todas las órdenes de producción han sido creadas.")


 