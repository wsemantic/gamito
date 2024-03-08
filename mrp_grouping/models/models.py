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
        sale_orders = sale_orders.filtered(lambda r: r.commitment_date).sorted(key=lambda r: r.commitment_date)

        groups = []
        current_group = []
        group_end_date = fields.Datetime.now()
        latest_end_date = fields.Datetime.now()
        start_gr_date = fields.Datetime.now()
        start_dates=self.find_max_reserved_date_for_work_centers(sale_orders)

        _logger.info("WSEM Inicio:")
        for order in sale_orders:
            _logger.info(f"WSEM itera orden : {order.name}")
            current_group.append(order)
            #products_by_phase se redefine actualizado con cada nueva orden
            products_by_phase = self._sort_products_by_phase(current_group)
            
            start_dates, end_dates = self._calculate_lead_times_by_phase(products_by_phase, start_dates)
            order.commitment_date = self.max_reserved_date_for_order(order, start_dates)
            
            group_end_date_old = group_end_date
            group_end_date = max(end_dates.values())
            _logger.info(f"WSEM fecha grupo : {group_end_date.strftime('%Y-%m-%d %H:%M:%S')}")

            if group_end_date >= start_gr_date + timedelta(days=self.daysgroup):
                if len(current_group) == 1:
                    _logger.info("WSEM primer grupo supera fecha")
                else:
                    # Elimino grupo que se pasa y actualizo datos
                    current_group.pop()
                    products_by_phase = self._sort_products_by_phase(current_group)
                    start_dates, end_dates = self._calculate_lead_times_by_phase(products_by_phase, start_dates)
                    group_end_date = max(end_dates.values())

                start_gr_date = group_end_date

                groups.append((products_by_phase, start_dates, end_dates))

                if len(groups) >= self.ngroups:
                    break

                current_group = []

        for group in groups:
            self._create_production_orders(*group)
            
    def max_reserved_date_for_order(self, orden, start_dates):

        fecha_maxima = False
        
        for linea in orden.order_line:
            product = linea.product_id
            if start_dates[product]:
                if not fecha_maxima or start_dates.get(product, fields.Datetime.now()) > fecha_maxima:
                    fecha_maxima = start_dates.get(product, fields.Datetime.now())        
        return fecha_maxima or fields.Datetime.now()
        

    def find_max_reserved_date_for_work_centers(self, ordenes_venta):
        max_dates_per_product = {}

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
                            if wc_max_date > max_date:
                                max_date = wc_max_date

                    # Actualizar la fecha máxima para el producto
                    if product.id not in max_dates_per_product or max_date > max_dates_per_product[product.id]:
                        max_dates_per_product[product.id] = max_date

        return max_dates_per_product

    def _calculate_lead_times_by_phase(self, products_by_phase, start_dates):

        end_dates = defaultdict(lambda: fields.Datetime.now())
        workcenter_sched=defaultdict(lambda: fields.Datetime.now())
        workcenter_of_products={}
        
        calcular fechas de finalziacion por centro de trabajo, y la fecha start es la final del mismo centro para la fase anterior
        if products_by_phase.keys():
            rangef=max(products_by_phase.keys()) + 1
            _logger.info(f"WSEM dbg {rangef} contenido {1 in products_by_phase}" )
            for phase in range(rangef):
                for product in products_by_phase[phase]:
                    #start basado en ordenes existentes o bacth anteriores, antes de ejecutarse por primera vez este batch
                    start_date_init=start_dates.get(product.id, fields.Datetime.now())
                    #tiempo total en que se liberara el centro de este producto en esta planificacion
                    lead_time_wc_reservado= self._get_leadtime( workcenter_sched, workcenter_of_products, product )
                    
                    self._calculate_product_lead_time(product,workcenter_sched,workcenter_of_products)
                    new_lead_time= self._get_leadtime( workcenter_sched, workcenter_of_products, product )
                    incr_lead_time=new_lead_time-lead_time_wc_reservado
                    start_dates[product.id] = start_date_init + timedelta(days=lead_time_wc_reservado/60.0)
                    
                    end_date = start_dates[product.id] + timedelta(days=incr_lead_time/60.0)
                    end_dates[product.id] = end_date                    
                    
        else:
            _logger.info(f"WSEM no hay fases" )

        return start_dates, end_dates

    def _get_leadtime(self, workcenter_sched, workcenter_of_products, product ):
        wid=workcenter_of_products.get(product.id,0)
        if wid==0 return 0
        return workcenter_sched.get(wid,0)
 
    def _sort_products_by_phase(self, sale_orders):
        products_by_phase = defaultdict(lambda: defaultdict(float))

        for order in sale_orders:
            for line in order.order_line:
                product = line.product_id
                bom = self.env['mrp.bom']._bom_find(product)[product]                                                                                                                                                               
                                                                             
                phase = 0 if not bom else max(self._get_bom_phases(bom))
                                                         
                products_by_phase[phase][product] += line.product_uom_qty

        return products_by_phase

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

    def _calculate_product_lead_time(self, product,workcenter_sched,workcenter_of_products):
        
        bom = self.env['mrp.bom']._bom_find(product)[product]
        
        if bom:
            for operation in bom.operation_ids:
                workcenter = operation.workcenter_id
                cycle_time = sum(wc_line.time_cycle for wc_line in workcenter.routing_line_ids)
                workcenter_sched[workcenter.id]=workcenter_sched.get(workcenter.id,0.0)+cycle_time / workcenter.default_capacity       
                workcenter_of_products[product.id]=workcenter.id
                _logger.info(f"WSEM cycle t:{cycle_time} leadtime:{workcenter_sched[workcenter.id]}")               

            for line in bom.bom_line_ids:
                self._calculate_product_lead_time(line.product_id,workcenter_sched,workcenter_of_products)
                _logger.info("WSEM añadido extra")

    def _create_production_orders(self, products_by_phase, start_dates, end_dates):
        """
        Crear órdenes de producción basadas en los productos agrupados por fase,
        considerando las cantidades acumuladas de cada producto.
        """
        ProductionOrder = self.env['mrp.production']
        for phase, products_info in products_by_phase.items():
            for product, quantity in products_info.items():
                bom = self.env['mrp.bom']._bom_find(product)[product]
                if not bom:
                    _logger.info(f"WSEM No se encontró BOM para el producto {product.display_name}. Se omite la creación de la orden de producción.")
                    continue
                
                # Preparar datos para la creación de la orden de producción
                production_data = {
                    'product_id': product.id,
                    'product_qty': quantity,
                    'bom_id': bom.id,
                    'date_planned_start': start_dates[product.id],
                    'date_planned_finished': end_dates[product.id],
                    'company_id': self.env.company.id,  # Asume que la compañía se toma del contexto actual
                }

                # Opcional: establecer el usuario si está disponible en el contexto/env
                if self.env.user and self.env.user.id:
                    production_data['user_id'] = self.env.user.id

                # Crear la orden de producción
                production_order = ProductionOrder.create(production_data)

                _logger.info(f"WSEM Orden de producción creada: {production_order.name} para el producto {product.display_name} con cantidad {quantity}.")

        _logger.info("WSEM  Todas las órdenes de producción han sido creadas.")


 