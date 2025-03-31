from odoo import models, api

class ReportInvoiceNet(models.AbstractModel):
    _name = 'report.ws_gamito.invoice.net'
    _description = 'Reporte Neto de Facturación ws_gamito'

    @api.model
    def _get_report_values(self, docids, data=None):
        # Obtener parámetros enviados desde el wizard
        cliente_id = data.get('form', {}).get('cliente_id')
        fecha_inicio = data.get('form', {}).get('fecha_inicio')
        fecha_fin = data.get('form', {}).get('fecha_fin')

        # Definir dominio para filtrar las líneas de facturas y abonos
        domain = [
            ('partner_id', '=', cliente_id),
            ('date', '>=', fecha_inicio),
            ('date', '<=', fecha_fin),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
        ]
        # Campos a sumar y agrupar
        fields = ['price_total', 'net_weight', 'quantity']
        group_by = ['product_id', 'packaging_id']

        agrupados = self.env['account.move.line'].read_group(domain, fields, group_by)

        line_data = []
        total_amount = 0.0
        total_net_weight = 0.0
        total_units = 0.0

        for grupo in agrupados:
            importe = grupo.get('price_total', 0.0)
            peso = grupo.get('net_weight', 0.0)
            unidades = grupo.get('quantity', 0.0)
            
            # Ejemplo de cálculo del % de importe devuelto.
            # Aquí se supone que no se han considerado devoluciones (0%).
            importe_devueltos = 0.0  
            porcentaje_devuelto = (importe_devueltos / importe * 100) if importe else 0.0

            line_data.append({
                'product_name': grupo.get('product_id')[1] if grupo.get('product_id') else '',
                'packaging_name': grupo.get('packaging_id')[1] if grupo.get('packaging_id') else '',
                'total_amount': importe,
                'return_percentage': porcentaje_devuelto,
                'net_weight': peso,
                'units': unidades,
            })
            total_amount += importe
            total_net_weight += peso
            total_units += unidades

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
