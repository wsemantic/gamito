from odoo import models, api
from odoo.tools import float_utils
import logging

_logger = logging.getLogger(__name__)

class ReportInvoiceNet(models.AbstractModel):
    _name = 'report.ws_gamito.invoice_net_template'
    _description = 'Reporte Neto de Facturación ws_gamito'

    @api.model
    def _get_report_values(self, docids, data=None):
        _logger.info("WS Iniciando _get_report_values")
        cliente_id = data.get('form', {}).get('cliente_id')
        fecha_inicio = data.get('form', {}).get('fecha_inicio')
        fecha_fin = data.get('form', {}).get('fecha_fin')

        _logger.info(f"WS Parámetros: cliente_id={cliente_id}, fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}")

        move_domain = [
            ('partner_id', '=', cliente_id),
            ('date', '>=', fecha_inicio),
            ('date', '<=', fecha_fin),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '=', 'posted'),
        ]
        moves = self.env['account.move'].search(move_domain)
        _logger.info(f"WS Se encontraron {len(moves)} facturas/notas de crédito")

        invoice_lines = self.env['account.move.line'].search([('move_id', 'in', moves.ids)])
        _logger.info(f"WS Se encontraron {len(invoice_lines)} líneas de factura")

        line_data_dict = {}
        for line in invoice_lines:
            product_id = line.product_id.id if line.product_id else False
            packaging_id = False
            packaging_name = 'Sin empaquetado'

            if line.sale_line_ids:
                sale_line = line.sale_line_ids[0]
                packaging_id = sale_line.product_packaging_id.id if sale_line.product_packaging_id else False
                packaging_name = sale_line.product_packaging_id.name if sale_line.product_packaging_id else 'Sin empaquetado'
            else:
                _logger.debug(f"WS Línea de factura {line.id} sin pedido de venta asociado")

            key = (product_id, packaging_id)
            if key not in line_data_dict:
                line_data_dict[key] = {
                    'product_id': product_id,
                    'packaging_id': packaging_id,
                    'packaging_name': packaging_name,
                    'total_amount': 0.0,
                    'returned_amount': 0.0,
                    'total_units': 0.0,
                    'total_net_weight': 0.0,
                }

            importe = float_utils.float_round(line.price_total, precision_digits=2)
            unidades = float_utils.float_round(line.quantity, precision_digits=2)
            net_weight = float_utils.float_round(line.product_id.product_tmpl_id.net_weight, precision_digits=2) if line.product_id else 0.0
            peso_total = float_utils.float_round(net_weight * unidades, precision_digits=2)

            if line.move_id.move_type == 'out_invoice':
                line_data_dict[key]['total_amount'] += importe
                line_data_dict[key]['total_units'] += unidades
                line_data_dict[key]['total_net_weight'] += peso_total
            elif line.move_id.move_type == 'out_refund':
                line_data_dict[key]['returned_amount'] += importe
                line_data_dict[key]['total_units'] -= unidades
                line_data_dict[key]['total_net_weight'] -= peso_total

        _logger.info(f"WS Se procesaron {len(line_data_dict)} grupos únicos de producto y empaquetado")

        line_data = []
        total_amount = 0.0
        total_net_weight = 0.0
        total_units = 0.0
        total_returned_amount = 0.0

        for key, values in line_data_dict.items():
            product_id = values['product_id']
            product_name = self.env['product.product'].browse(product_id).name if product_id else 'Sin producto'

            # Redondear los valores acumulados
            total_amount_line = float_utils.float_round(values['total_amount'], precision_digits=2)
            returned_amount_line = float_utils.float_round(values['returned_amount'], precision_digits=2)
            porcentaje_devuelto = float_utils.float_round((returned_amount_line / total_amount_line * 100), precision_digits=2) if total_amount_line > 0 else 0.0
            net_weight_line = float_utils.float_round(values['total_net_weight'], precision_digits=2)
            units_line = float_utils.float_round(values['total_units'], precision_digits=2)

            line_data.append({
                'product_name': product_name,
                'packaging_name': values['packaging_name'],
                'total_amount': total_amount_line,
                'return_percentage': porcentaje_devuelto,
                'net_weight': net_weight_line,
                'units': units_line,
            })

            total_amount += total_amount_line
            total_returned_amount += returned_amount_line
            total_net_weight += net_weight_line
            total_units += units_line

        _logger.info("WS Finalizando _get_report_values")

        result = {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': [{
                'line_data': line_data,
                'total_amount': float_utils.float_round(total_amount, precision_digits=2),
                'total_returned_amount': float_utils.float_round(total_returned_amount, precision_digits=2),
                'total_net_weight': float_utils.float_round(total_net_weight, precision_digits=2),
                'total_units': float_utils.float_round(total_units, precision_digits=2),
            }],
            'data': data,
        }
        _logger.info(f"WS Resultado devuelto: {result}")
        return result