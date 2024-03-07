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

        _logger.info("WSEM Inicio:")
        for order in sale_orders:
            _logger.info(f"WSEM itera orden : {order.name}")
            current_group.append(order)
            products_by_phase = self._sort_products_by_phase(current_group)
            
            product_lead_times, start_dates, end_dates = self._calculate_lead_times_by_phase(products_by_phase, group_end_date)
            group_end_date_old = group_end_date
            group_end_date = max(end_dates.values())
            _logger.info(f"WSEM fecha grupo : {group_end_date.strftime('%Y-%m-%d %H:%M:%S')}")

            if group_end_date >= start_gr_date + timedelta(days=self.daysgroup):
                if len(current_group) == 1:
                    _logger.info("WSEM primer grupo supera fecha")
                else:
                    # Elimino grupo que se pasa y actualizo datos
                    current_group.pop()
                    product_lead_times, start_dates, end_dates = self._calculate_lead_times_by_phase(products_by_phase, group_end_date_old)
                    group_end_date = max(end_dates.values())

                start_gr_date = group_end_date

                groups.append((products_by_phase, product_lead_times, start_dates, end_dates))

                if len(groups) >= self.ngroups:
                    break

                current_group = []

        for group in groups:
            self._create_production_orders(*group)

    def _calculate_lead_times_by_phase(self, products_by_phase, start_date):
        product_lead_times = defaultdict(lambda: 0.0)
        start_dates = defaultdict(lambda: fields.Datetime.now())
        end_dates = defaultdict(lambda: fields.Datetime.now())
       
        if products_by_phase.keys():
            rangef=max(products_by_phase.keys()) + 1
            _logger.info(f"WSEM dbg {rangef} contenido {1 in products_by_phase}" )
            for phase in range(rangef):
                if phase > 0:
                    start_date = end_dates[phase - 1]

                for product in products_by_phase[phase]:
                    lead_time = self._calculate_product_lead_time(product)
                    product_lead_times[product.id] = lead_time
                    start_dates[product.id] = start_date
                    end_date = start_date + timedelta(days=lead_time)
                    end_dates[product.id] = end_date
                    start_date = end_date
        else:
            _logger.info(f"WSEM no hay fases" )

        return product_lead_times, start_dates, end_dates

    def _sort_products_by_phase(self, sale_orders):
        products_by_phase = defaultdict(lambda: defaultdict(float))

        for order in sale_orders:
            for line in order.order_line:
                product = line.product_id
                bom = self.env['mrp.bom']._bom_find(product=product)                                                                                                                                                                   
                                                                             
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

    def _calculate_product_lead_time(self, product):
        lead_time = 0.0
        bom = self.env['mrp.bom']._bom_find(product)[product]
        if bom:
            for operation in bom.operation_ids:
                workcenter = operation.workcenter_id
                cycle_time = sum(wc_line.time_cycle for wc_line in workcenter.routing_line_ids)
                lead_time += cycle_time / workcenter.default_capacity

            for line in bom.bom_line_ids:
                lead_time += self._calculate_product_lead_time(line.product_id)

        return lead_time

    def _create_production_orders(self, products_by_phase, product_lead_times, start_dates, end_dates):
        """
        Crear órdenes de producción basadas en los productos agrupados por fase,
        considerando las cantidades acumuladas de cada producto.
        """
        ProductionOrder = self.env['mrp.production']
        for phase, products_info in products_by_phase.items():
            for product, quantity in products_info.items():
                bom = self.env['mrp.bom']._bom_find(product=product)
                if not bom:
                    _logger.warning(f"No se encontró BOM para el producto {product.display_name}. Se omite la creación de la orden de producción.")
                    continue
                
                # Preparar datos para la creación de la orden de producción
                production_data = {
                    'product_id': product.id,
                    'product_qty': quantity,
                    'bom_id': bom.id,
                    'date_planned_start': start_dates[product],
                    'date_planned_finished': end_dates[product],
                    'company_id': self.env.company.id,  # Asume que la compañía se toma del contexto actual
                }

                # Opcional: establecer el usuario si está disponible en el contexto/env
                if self.env.user and self.env.user.id:
                    production_data['user_id'] = self.env.user.id

                # Crear la orden de producción
                production_order = ProductionOrder.create(production_data)

                _logger.info(f"Orden de producción creada: {production_order.name} para el producto {product.display_name} con cantidad {quantity}.")

        _logger.info("Todas las órdenes de producción han sido creadas.")


 