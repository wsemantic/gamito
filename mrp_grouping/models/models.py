from odoo import api, fields, models
from collections import defaultdict
from datetime import timedelta

class MrpDateGrouping(models.TransientModel):
    _name = 'mrp.date.grouping'
    _description = 'Plan Production'

    daysgroup = fields.Integer(string='Number of Days to Group', default=7, required=True)
    ngroups = fields.Integer(string='Number of Groups to Plan', default=2, required=True)

    def mrp_planning(self):
        sale_orders = self.env['sale.order'].browse(self._context.get('active_ids'))
        sale_orders = sale_orders.filtered(lambda r: r.commitment_date).sorted(key=lambda r: r.commitment_date)


        # Calculate production time for each product
        product_lead_times = defaultdict(lambda: 0.0)
        for product in sale_orders.mapped('order_line.product_id'):
            lead_time = self._calculate_product_lead_time(product)
            product_lead_times[product.id] = lead_time

        groups = []
        current_group = []
        group_end_date = fields.Datetime.now()

        for order in sale_orders:
            if order.commitment_date >= group_end_date + timedelta(days=self.daysgroup):
                if current_group:
                    groups.append(current_group)
                    if len(groups) >= self.ngroups:
                        break
                current_group = [order]
                group_end_date = order.commitment_date + timedelta(days=self.daysgroup)
            else:
                current_group.append(order)

            for line in order.order_line:
                product_lead_time = product_lead_times[line.product_id.id]
                line.commitment_date = order.commitment_date + timedelta(days=product_lead_time)

        if current_group:
            groups.append(current_group)

        for group in groups:
            self._create_production_orders(group)

    def _calculate_product_lead_time(self, product):
        lead_time = 0.0
        bom = self.env['mrp.bom']._bom_find(product)
        if bom:
            for operation in bom.operation_ids:
                workcenter = operation.workcenter_id
                cycle_time = sum(wc_line.time_cycle for wc_line in workcenter.routing_line_ids)
                lead_time += cycle_time / workcenter.capacity_per_cycle

            for line in bom.bom_line_ids:
                lead_time += self._calculate_product_lead_time(line.product_id)

        return lead_time

    def _create_production_orders(self, sale_orders):
        production_orders = self.env['mrp.production']

        for order in sale_orders:
            for line in order.order_line:
                bom = self.env['mrp.bom']._bom_find(line.product_id)
                if bom:
                    production_order = production_orders.create({
                        'product_id': line.product_id.id,
                        'product_qty': line.product_uom_qty,
                        'bom_id': bom.id,
                        'sale_order_id': order.id,
                        'sale_order_line_id': line.id,
                        'date_planned_start': order.commitment_date,
                        'user_id': order.user_id.id,
                        'company_id': order.company_id.id,
                    })

                    production_orders |= production_order

                    self._create_production_orders_recursive(production_order, bom)

        return production_orders

    def _create_production_orders_recursive(self, production_order, bom):
        for bom_line in bom.bom_line_ids:
            child_bom = self.env['mrp.bom']._bom_find(bom_line.product_id)
            if child_bom:
                child_production_order = production_order.procurement_group_id.mrp_production_ids.create({
                    'product_id': bom_line.product_id.id,
                    'product_qty': bom_line.product_qty * production_order.product_qty,
                    'bom_id': child_bom.id,
                    'sale_order_id': production_order.sale_order_id.id,
                    'date_planned_start': production_order.date_planned_start,
                    'user_id': production_order.user_id.id,
                    'company_id': production_order.company_id.id,
                })

                self._create_production_orders_recursive(child_production_order, child_bom)