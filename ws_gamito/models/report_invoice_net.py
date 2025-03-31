from odoo import models, api

class ReportInvoiceNet(models.AbstractModel):
    _name = 'report.ws_gamito.invoice.net'
    _description = 'Reporte Neto de Facturación ws_gamito'

    @api.model
    def _get_report_values(self, docids, data=None):
        cliente_id = data.get('form', {}).get('cliente_id')
        fecha_inicio = data.get('form', {}).get('fecha_inicio')
        fecha_fin = data.get('form', {}).get('fecha_fin')

        domain = [
            ('partner_id', '=', cliente_id),
            ('date', '>=', fecha_inicio),
            ('date', '<=', fecha_fin),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
        ]

        fields = ['price_total', 'quantity']  # Campos directos de account.move.line
        group_by = ['product_id', 'packaging_id']

        agrupados = self.env['account.move.line'].read_group(domain, fields, group_by)

        line_data = []
        total_amount = 0.0
        total_net_weight = 0.0
        total_units = 0.0

        for grupo in agrupados:
            importe = grupo.get('price_total', 0.0)
            unidades = grupo.get('quantity', 0.0)
            product_id = grupo.get('product_id')[0] if grupo.get('product_id') else False
            packaging_id = grupo.get('packaging_id')[0] if grupo.get('packaging_id') else False

            # Obtener el net_weight desde product.product
            product = self.env['product.product'].browse(product_id) if product_id else False
            net_weight = product.product_tmpl_id.net_weight if product else 0.0
            # Multiplicar por la cantidad para obtener el peso neto total de la línea
            peso_total = net_weight * unidades

            importe_devueltos = 0.0  # Ejemplo, ajustar según lógica real
            porcentaje_devuelto = (importe_devueltos / importe * 100) if importe else 0.0

            line_data.append({
                'product_name': grupo.get('product_id')[1] if grupo.get('product_id') else '',
                'packaging_name': grupo.get('packaging_id')[1] if grupo.get('packaging_id') else '',
                'total_amount': importe,
                'return_percentage': porcentaje_devuelto,
                'net_weight': peso_total,  # Peso neto total (net_weight por unidad * cantidad)
                'units': unidades,
            })
            total_amount += importe
            total_net_weight += peso_total
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