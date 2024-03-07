from odoo import models, fields, api
from datetime import datetime, timedelta
from collections import defaultdict

class MrpDateGrouping(models.TransientModel):
    _name = 'mrp.date.grouping'
    _description = 'Wizard for Date-Based Grouping in MRP'

    daysgroup = fields.Integer("Número de días a agrupar", required=True, default=1)
    ngroups = fields.Integer("Número de grupos a planificar", required=True, default=1)

    def mrp_planning(self):     
        active_ids = self.env.context.get('active_ids')
        orders = self.env['sale.order'].browse(active_ids).sorted(key=lambda o: o.commitment_date)

        current_batch = []
        batches_processed = 0
        last_batch_end_date = datetime.now()

        for order in orders:
            current_batch.append(order)
            # Procesar el batch actual para ajustar las fechas de entrega
            batch_end_date = self._process_batch(current_batch, last_batch_end_date)

            if batch_end_date > last_batch_end_date + timedelta(days=self.daysgroup):
                # Si se supera el límite de días para el batch actual, iniciar un nuevo batch
                batches_processed += 1
                if batches_processed >= self.ngroups:
                    break  # Finalizar si se alcanza el número máximo de grupos
                current_batch = [order]  # Iniciar un nuevo batch con el pedido actual
                last_batch_end_date = batch_end_date
            else:
                last_batch_end_date = batch_end_date

        # Aquí se puede agregar lógica para manejar las órdenes de trabajo resultantes del último batch procesado
        # y cualquier acción final después de procesar todos los batches.

        return {'type': 'ir.actions.act_window_close'}

    def _process_batch(self, batch, start_date):
        # Diccionario para agrupar la demanda por producto, operación y centro de trabajo
        product_demand = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

        # Recorrer cada pedido en el batch para procesar sus productos
        for order in batch:
            for line in order.order_line:
                product = line.product_id
                self._aggregate_product_demand(product, line.product_uom_qty, product_demand)

        # Aquí se procesaría la demanda agregada para calcular la nueva fecha de entrega
        # Simulación de cómo se podría calcular el tiempo total basado en la demanda agregada
        batch_end_date = start_date
        for product, operations in product_demand.items():
            for operation, workcenters in operations.items():
                for workcenter, demand in workcenters.items():
                    # Simular el cálculo del tiempo necesario basado en la demanda agregada
                    # Este es solo un ejemplo; necesitarás implementar tu lógica de cálculo
                    batch_end_date += timedelta(hours=demand / workcenter.capacity_per_hour)

        return batch_end_date

    def _aggregate_product_demand(self, product, quantity, product_demand):
        # Verificar si el producto tiene una BOM
        bom = self.env['mrp.bom']._bom_find(product=product)
        if bom:
            # Si el producto tiene BOM, procesar recursivamente los componentes
            for bom_line in bom.bom_line_ids:
                self._aggregate_product_demand(bom_line.product_id, bom_line.product_qty * quantity, product_demand)
        else:
            # Para productos sin BOM, agregar la demanda
            # Aquí asumimos que tienes una forma de determinar la operación y el centro de trabajo
            # para el producto. Esto podría requerir lógica adicional basada en tu configuración específica.
            operation = "OperaciónPredeterminada"  # Este valor debe determinarse según tu lógica
            workcenter = self.env['mrp.workcenter'].browse(1)  # Ejemplo: obtiene el primer centro de trabajo
            product_demand[product][operation][workcenter] += quantity