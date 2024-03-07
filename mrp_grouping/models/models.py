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

        _logger.info(f"WSEM Inicio:")
        for order in sale_orders:
            _logger.info(f"WSEM itera orden : {order.name}")
            current_group.append(order)
            product_lead_times, start_dates, end_dates = self._calculate_lead_times_by_phase(current_group,group_end_date)
            group_end_date_old=group_end_date;
            group_end_date = max(end_dates.values())
            _logger.info(f"WSEM fecha grupo : {group_end_date.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if group_end_date >= start_gr_date + timedelta(days=self.daysgroup):         
                current_group.pop()
                product_lead_times, start_dates, end_dates = self._calculate_lead_times_by_phase(current_group,group_end_date_old)
                group_end_date = max(end_dates.values())
                start_gr_date=group_end_date
                
                groups.append((current_group, product_lead_times, start_dates, end_dates))
                                
                if len(groups) >= self.ngroups:
                    break
                    
                current_group = []                 

        for group, product_lead_times, start_dates, end_dates in groups:
            self._create_production_orders(group, product_lead_times, start_dates, end_dates)

    def _calculate_lead_times_by_phase(self, sale_orders, start_date):
        product_lead_times = defaultdict(lambda: 0.0)
        start_dates = defaultdict(lambda: fields.Datetime.now())
        end_dates = defaultdict(lambda: fields.Datetime.now())
        products_by_phase = self._sort_products_by_phase(sale_orders)

        for phase in range(max(products_by_phase.keys()) + 1):
            if phase > 0:
                start_date = end_dates[phase - 1]

            for product in products_by_phase[phase]:
                lead_time = self._calculate_product_lead_time(product)
                product_lead_times[product.id] = lead_time
                start_dates[product.id] = start_date
                end_date = start_date + timedelta(days=lead_time)
                end_dates[product.id] = end_date
                start_date = end_date

        return product_lead_times, start_dates, end_dates

    def _sort_products_by_phase(self, sale_orders):
        products_by_phase = defaultdict(list)

        for order in sale_orders:
            for line in order.order_line:
                product = line.product_id                
                bom = self.env['mrp.bom']._bom_find(product)[product]
                if not bom:
                    _logger.info(f"WSEM no encontrado bom")
                    products_by_phase[0].append(product)
                else:
                    _logger.info(f"WSEM encontrado bom : {bom.display_name}")
                    phase = max(self._get_bom_phases(bom))
                    products_by_phase[phase].append(product)

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

    def _create_production_orders(self, sale_orders, product_lead_times, start_dates, end_dates):
        production_orders = self.env['mrp.production']

        for order in sale_orders:
            for line in order.order_line:
                bom = self.env['mrp.bom']._bom_find(line.product_id)[line.product_id]
                if bom:
                    production_order = production_orders.create({
                        'product_id': line.product_id.id,
                        'product_qty': line.product_uom_qty,
                        'bom_id': bom.id,
                        'sale_order_id': order.id,
                        'sale_order_line_id': line.id,
                        'date_planned_start': start_dates[line.product_id.id],
                        'date_planned_finished': end_dates[line.product_id.id],
                        'user_id': order.user_id.id,
                        'company_id': order.company_id.id,
                    })

                    production_orders |= production_order

                    self._create_production_orders_recursive(production_order, bom, start_dates, end_dates)

        return production_orders

    def _create_production_orders_recursive(self, production_order, bom, start_dates, end_dates):
        for bom_line in bom.bom_line_ids:
            child_bom = self.env['mrp.bom']._bom_find(bom_line.product_id)[bom_line.product_id]
            if child_bom:
                child_production_order = production_order.procurement_group_id.mrp_production_ids.create({
                    'product_id': bom_line.product_id.id,
                    'product_qty': bom_line.product_qty * production_order.product_qty,
                    'bom_id': child_bom.id,
                    'sale_order_id': production_order.sale_order_id.id,
                    'date_planned_start': start_dates[bom_line.product_id.id],
                    'date_planned_finished': end_dates[bom_line.product_id.id],
                    'user_id': production_order.user_id.id,
                    'company_id': production_order.company_id.id,
                })

                self._create_production_orders_recursive(child_production_order, child_bom, start_dates, end_dates)