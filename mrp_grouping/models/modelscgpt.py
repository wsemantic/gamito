from odoo import models, fields, api
import datetime

class MrpDateGrouping(models.TransientModel):
    _name = 'mrp.date.grouping'
    _description = 'MRP Date Grouping'

    daysgroup = fields.Integer("Number of Days to Group")
    ngroups = fields.Integer("Number of Groups to Plan")

    @api.model
    def default_get(self, fields):
        res = super(MrpDateGrouping, self).default_get(fields)
        # Default values can be set here if needed
        return res
        
    def calculate_batch_production_time(self, batch_orders):
        """
        Calcula el tiempo de producción para un lote de órdenes de venta basado en la demanda agregada.
        :param batch_orders: Órdenes de venta en el lote actual.
        :return: Tiempo total estimado de producción para el lote.
        """
        # Diccionario para acumular la demanda total por producto
        product_demand = {}

        # Agregar las demandas de productos de todas las órdenes en el lote
        for order in batch_orders:
            for line in order.order_line:
                product = line.product_id
                product_demand[product] = product_demand.get(product, 0) + line.product_uom_qty

        # Calcular el tiempo de producción basado en la demanda agregada
        total_production_time = 0
        for product, qty in product_demand.items():
            bom = self.env['mrp.bom']._bom_find(product=product)
            if bom:
                product_time, _ = self.calculate_product_time(bom, quantity=qty)
                total_production_time += product_time

        return total_production_time

    def mrp_planning(self):
        SaleOrder = self.env['sale.order']
        selected_orders = SaleOrder.browse(self._context.get('active_ids', [])).sorted(key=lambda r: r.commitment_date)
        
        n_inicio_grupo_actual = 0
        current_group = 0
        fecha_inicio_grupo_actual = fields.Date.today()

        while current_group < self.ngroups and n_inicio_grupo_actual < len(selected_orders):
            # Seleccionar órdenes para el lote actual hasta que se supere el límite de tiempo o se procesen todas las órdenes
            for next_order_index in range(n_inicio_grupo_actual, len(selected_orders)):
                batch_orders = selected_orders[n_inicio_grupo_actual:next_order_index + 1]
                total_production_time = self.calculate_batch_production_time(batch_orders)
                
                # Verificar si el tiempo de producción excede el límite para el lote actual
                if total_production_time > self.daysgroup * self.get_daily_production_capacity():
                    # Si se excede, procesar hasta la orden anterior
                    batch_orders = selected_orders[n_inicio_grupo_actual:next_order_index]
                    break

            # Actualizar fechas de entrega y otros procesos necesarios para el lote
            # ...

            # Preparar para el siguiente grupo
            current_group += 1
            n_inicio_grupo_actual = next_order_index + 1  # Empezar el siguiente grupo con la siguiente orden

        # Lógica adicional para manejar cualquier post-proceso necesario después de planificar todos los grupos


    def get_production_capacity_per_day(self):
        """
        Devuelve la capacidad de producción por día del centro de trabajo.
        Esto puede variar dependiendo de la configuración específica de tu centro de trabajo.
        :return: Capacidad de producción por día en horas.
        """
        # Este es un valor de ejemplo. Debes ajustarlo según la capacidad real de tu centro de trabajo.
        return 8 * number_of_work_centers  # Por ejemplo, 8 horas por día por el número de centros de trabajo


    def calculate_product_time(self, bom, quantity=1.0):
        """
        Calcular el tiempo de producción para un producto específico basado en su BOM.
        """
        time = 0
        # Considerar tanto las operaciones directas como las sub-operaciones (recursión en BOMs)
        for line in bom.bom_line_ids:
            operation_time = line.operation_id.time_cycle * line.product_qty * quantity
            time += operation_time
            # Recursión para componentes que a su vez tienen BOM
            sub_bom = self.env['mrp.bom']._bom_find(product=line.product_id)
            if sub_bom:
                sub_time, _ = self.calculate_product_time(sub_bom, quantity=line.product_qty * quantity)
                time += sub_time

        # Considerar la capacidad general del centro de producción para ajustar el tiempo total
        # Esto puede implicar dividir el tiempo entre el número de máquinas disponibles si se pueden realizar operaciones en paralelo
        # time_adjusted = time / number_of_machines if parallel_operations_allowed else time

        return time, completion_date


    def create_production_orders(self, order, production_time):
        for line in order.order_line:
            product = line.product_id

            # Encuentra o crea una Lista de Materiales (BOM) para el producto
            bom = self.env['mrp.bom']._bom_find(product=product)
            if not bom:
                # Aquí se podría manejar la creación de una BOM si es necesario
                # Esto dependerá de la lógica de negocio y cómo se manejen normalmente las BOMs en el sistema
                continue  # Si no hay BOM, saltamos este producto

            # Crea una orden de producción
            production_order_vals = {
                'product_id': product.id,
                'product_qty': line.product_uom_qty,
                'product_uom_id': product.uom_id.id,
                'bom_id': bom.id,
                'origin': order.name,
                'date_planned_start': datetime.datetime.now(),  # Ejemplo de programación inmediata
                # 'date_planned_finished': calculado basado en el tiempo de producción y la capacidad
            }

            production_order = self.env['mrp.production'].create(production_order_vals)

            # Programar la orden de producción si es necesario
            # Esto puede incluir la asignación de tiempos específicos basados en la disponibilidad de las máquinas y/o trabajadores
            # También puedes lanzar aquí el cálculo de la planificación si tu sistema lo soporta automáticamente
            # production_order.button_plan()

            # Nota: Este es un ejemplo básico. Dependiendo de los detalles y requerimientos específicos
