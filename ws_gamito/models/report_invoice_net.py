from odoo import models, api
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
        desglosar_empaquetado = data.get('form', {}).get('desglosar_empaquetado', False)

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
            packaging_name = False

            if desglosar_empaquetado:
                if line.sale_line_ids:
                    sale_line = line.sale_line_ids[0]
                    packaging_id = sale_line.product_packaging_id.id if sale_line.product_packaging_id else False
                    packaging_name = sale_line.product_packaging_id.name if sale_line.product_packaging_id else False
                if not packaging_name and line.product_id:
                    packaging = line.product_id.packaging_ids[:1]
                    packaging_id = packaging.id if packaging else False
                    packaging_name = packaging.name if packaging else 'Sin empaquetado'
                if not packaging_name:
                    _logger.warning(f"WS Línea de factura {line.id} sin empaquetado asociado para {line.product_id.name}")

            key = (product_id, packaging_id) if desglosar_empaquetado else (product_id,)
            if key not in line_data_dict:
                line_data_dict[key] = {
                    'product_id': product_id,
                    'packaging_id': packaging_id,
                    'packaging_name': packaging_name or 'Sin empaquetado' if desglosar_empaquetado else '',
                    'total_amount': 0.0,  # Con IVA, incluyendo todo para mostrar
                    'total_amount_no_tax': 0.0,  # Sin IVA, incluyendo todo para mostrar
                    'returned_amount': 0.0,  # Solo para notas de crédito no rappel
                    'total_units': 0.0,
                    'returned_units': 0.0,
                    'total_net_weight': 0.0,
                    'default_code': line.product_id.default_code if line.product_id else '',
                    'total_amount_entregado': 0.0,  # Nuevo: solo para facturas de ventas no rappel
                }

            importe = round(line.price_total, 2)  # Con IVA
            importe_sin_iva = round(line.price_subtotal, 2)  # Sin IVA
            unidades = round(line.quantity, 2)
            net_weight = round(line.product_id.product_tmpl_id.net_weight, 2) if line.product_id else 0.0
            peso_total = round(net_weight * unidades, 2)

            signo = 1 if line.move_id.move_type == 'out_invoice' else -1

            # Detectar si es un producto "rappel" por su referencia "100006"
            is_rappel = line.product_id.default_code == '100006' if line.product_id else False

            # Acumular total_amount y total_amount_no_tax para mostrar, incluyendo todo
            line_data_dict[key]['total_amount'] += round(signo * importe, 2)
            line_data_dict[key]['total_amount_no_tax'] += round(signo * importe_sin_iva, 2)
            line_data_dict[key]['total_units'] += round(signo * unidades, 2)
            line_data_dict[key]['total_net_weight'] += round(signo * peso_total, 2)

            if line.move_id.move_type == 'out_refund':
                if not is_rappel:
                    line_data_dict[key]['returned_amount'] += round(importe, 2)  # Solo no rappels
                    line_data_dict[key]['returned_units'] += round(unidades, 2)
            elif line.move_id.move_type == 'out_invoice' and not is_rappel:
                # Acumular total_amount_entregado solo para facturas de ventas no rappel
                line_data_dict[key]['total_amount_entregado'] += round(importe, 2)
            else:
                _logger.info(f"WS Facturado {line.product_id.name} {importe}")

        _logger.info(f"WS Se procesaron {len(line_data_dict)} grupos únicos de producto y empaquetado")

        line_data = []
        total_amount = 0.0
        total_amount_no_tax = 0.0
        total_net_weight = 0.0
        total_units = 0.0
        total_returned_amount = 0.0
        total_returned_units = 0.0
        total_amount_entregado_global = 0.0  # Para total general

        for key, values in line_data_dict.items():
            product_id = values['product_id']
            product_name = self.env['product.product'].browse(product_id).name if product_id else 'Sin producto'

            total_amount_line = round(values['total_amount'], 2)
            total_amount_no_tax_line = round(values['total_amount_no_tax'], 2)
            returned_amount_line = round(values['returned_amount'], 2)
            total_amount_entregado_line = round(values['total_amount_entregado'], 2)
                                                                                                                              

            # Calcular porcentaje devuelto usando total_amount_entregado_line
            porcentaje_devuelto = round((returned_amount_line / total_amount_entregado_line * 100), 2) if total_amount_entregado_line > 0 else 0.0

            _logger.info(f"WS Producto: {product_name}, Total Ventas Sin Rappel: {total_amount_entregado_line}, Retornado: {returned_amount_line}, Porcentaje: {porcentaje_devuelto}")

            net_weight_line = round(values['total_net_weight'], 2)
            units_line = round(values['total_units'], 2)
            returned_units_line = round(values['returned_units'], 2)

            line_data.append({
                'product_name': product_name,
                'default_code': values['default_code'],
                'packaging_name': values['packaging_name'],
                'total_amount_no_tax': "{:.2f}".format(total_amount_no_tax_line),
                'total_amount': "{:.2f}".format(total_amount_line),
                                                            
                'return_percentage': "{:.2f}".format(porcentaje_devuelto),
                'net_weight': "{:.2f}".format(net_weight_line),
                'units': "{:.2f}".format(units_line),
                'returned_units': "{:.2f}".format(returned_units_line),
            })

            total_amount += total_amount_line
            total_amount_no_tax += total_amount_no_tax_line
            total_returned_amount += returned_amount_line
            total_net_weight += net_weight_line
            total_units += units_line
            total_returned_units += returned_units_line
            total_amount_entregado_global += total_amount_entregado_line

        # Ordenar line_data por default_code de manera ascendente
        line_data = sorted(line_data, key=lambda x: (x.get('default_code') or '').lower())

        # Calcular total_return_percentage usando total_amount_entregado_global
        total_return_percentage = round((total_returned_amount / total_amount_entregado_global * 100), 2) if total_amount_entregado_global > 0 else 0.0
        _logger.info(f"WS Totales: Total Ventas Sin Rappel: {total_amount_entregado_global}, Retornado: {total_returned_amount}, Porcentaje: {total_return_percentage}")

        result = {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': [{
                'line_data': line_data,
                'total_amount': "{:.2f}".format(round(total_amount, 2)),
                'total_amount_no_tax': "{:.2f}".format(round(total_amount_no_tax, 2)),
                'total_returned_amount': "{:.2f}".format(round(total_returned_amount, 2)),
                'total_net_weight': "{:.2f}".format(round(total_net_weight, 2)),
                'total_units': "{:.2f}".format(round(total_units, 2)),
                'total_returned_units': "{:.2f}".format(round(total_returned_units, 2)),
                                                                          
                'total_return_percentage': "{:.2f}".format(total_return_percentage),
            }],
            'data': data,
        }
        _logger.info(f"WS Resultado devuelto: {result}")
        return result