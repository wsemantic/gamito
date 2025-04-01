from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class ReportInvoiceNet(models.AbstractModel):
    _name = 'report.ws_gamito.invoice.net'
    _description = 'Reporte Neto de Facturación ws_gamito'

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info("WS Iniciando _get_report_values")
        cliente_id = data.get('form', {}).get('cliente_id')
        fecha_inicio = data.get('form', {}).get('fecha_inicio')
        fecha_fin = data.get('form', {}).get('fecha_fin')

        _logger.info(f"WS Parámetros: cliente_id={cliente_id}, fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}")

        domain = [
            ('partner_id', '=', cliente_id),
            ('date', '>=', fecha_inicio),
            ('date', '<=', fecha_fin),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
        ]

        # Buscar todas las líneas de factura que cumplen el dominio
        invoice_lines = self.env['account.move.line'].search(domain)
        _logger.info(f"WS Se encontraron {len(invoice_lines)} líneas de factura")

        # Diccionario para agrupar por producto y empaquetado
        line_data_dict = {}
        for line in invoice_lines:
            product_id = line.product_id.id if line.product_id else False
            packaging_id = False
            packaging_name = 'Sin empaquetado'

            # Verificar si hay líneas de venta asociadas
            if line.sale_line_ids:
                # Tomamos la primera línea de venta (ajusta si necesitas otra lógica)
                sale_line = line.sale_line_ids[0]
                packaging_id = sale_line.product_packaging.id if sale_line.product_packaging else False
                packaging_name = sale_line.product_packaging.name if sale_line.product_packaging else 'Sin empaquetado'
            else:
                _logger.debug(f"WS Línea de factura {line.id} sin pedido de venta asociado")

            # Clave única para agrupar
            key = (product_id, packaging_id)
            if key not in line_data_dict:
                line_data_dict[key] = {
                    'product_id': product_id,
                    'packaging_id': packaging_id,
                    'packaging_name': packaging_name,
                    'total_amount': 0.0,
                    'total_units': 0.0,
                    'total_net_weight': 0.0,
                }

            # Calcular valores
            importe = line.price_total
            unidades = line.quantity
            net_weight = line.product_id.product_tmpl_id.net_weight if line.product_id else 0.0
            peso_total = net_weight * unidades

            line_data_dict[key]['total_amount'] += importe
            line_data_dict[key]['total_units'] += unidades
            line_data_dict[key]['total_net_weight'] += peso_total

        _logger.info(f"WS Se procesaron {len(line_data_dict)} grupos únicos de producto y empaquetado")

        # Convertir el diccionario en lista para el informe
        line_data = []
        total_amount = 0.0
        total_net_weight = 0.0
        total_units = 0.0

        for key, values in line_data_dict.items():
            product_id = values['product_id']
            product_name = self.env['product.product'].browse(product_id).name if product_id else 'Sin producto'

            # Aquí podrías calcular el porcentaje de devolución si tienes la lógica
            importe_devueltos = 0.0  # Ajusta según tu necesidad
            porcentaje_devuelto = (importe_devueltos / values['total_amount'] * 100) if values['total_amount'] else 0.0

            line_data.append({
                'product_name': product_name,
                'packaging_name': values['packaging_name'],
                'total_amount': values['total_amount'],
                'return_percentage': porcentaje_devuelto,
                'net_weight': values['total_net_weight'],
                'units': values['total_units'],
            })
            total_amount += values['total_amount']
            total_net_weight += values['total_net_weight']
            total_units += values['total_units']

        _logger.info("WS Finalizando _get_report_values")

        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': [{
                'line_data': line_data,
                'total_amount': total_amount,
                'total_net_weight': total_net_weight,
                'total_units': total_units,
            }],
            'data': data,
        }