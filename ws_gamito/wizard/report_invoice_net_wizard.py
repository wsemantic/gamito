from odoo import models, fields
import base64
import io
import xlsxwriter

class ReportInvoiceNetWizard(models.TransientModel):
    _name = 'report.invoice.net.wizard'
    _description = 'Wizard para generar reporte neto de facturación'

    cliente_id = fields.Many2one('res.partner', string='Cliente', required=True)
    fecha_inicio = fields.Date(string='Fecha Inicio', required=True)
    fecha_fin = fields.Date(string='Fecha Fin', required=True)
    desglosar_empaquetado = fields.Boolean(string='Desglosar Empaquetado', default=False)

    def action_print_report(self):
        self.ensure_one()
        data = {
            'form': {
                'cliente_id': self.cliente_id.id,
                'fecha_inicio': self.fecha_inicio,
                'fecha_fin': self.fecha_fin,
                'desglosar_empaquetado': self.desglosar_empaquetado,
            }
        }
        return self.env.ref('ws_gamito.report_ws_gamito_invoice_net_action').report_action(self, data=data)

    def action_export_excel(self):
        self.ensure_one()
        data = {
            'form': {
                'cliente_id': self.cliente_id.id,
                'fecha_inicio': self.fecha_inicio,
                'fecha_fin': self.fecha_fin,
                'desglosar_empaquetado': self.desglosar_empaquetado,
            }
        }
        report = self.env['report.ws_gamito.invoice_net_template']
        result = report._get_report_values(self.ids, data=data)
        line_data = result['docs'][0]['line_data']

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Reporte Neto')

        # Definir formato para números con dos decimales
        number_format = workbook.add_format({'num_format': '0.00'})

        # Encabezados en el orden del reporte
        headers = [
            'Producto / Empaquetado',
            'Referencia',
            'CONSUMO REAL (Un.)',
            'DEVOLUCION (Un.)',
            '% Devuelto (€)',
            'Total Kg neto',
            'Total Fact. Base',
            'Total Fact con IVA'
        ]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        # Escribir datos
        for row, line in enumerate(line_data, start=1):
            # Construir el nombre del producto según desglosar_empaquetado
            name = (f"{line['product_name']} / {line['packaging_name']}"
                    if data['form']['desglosar_empaquetado'] and line['packaging_name']
                    else line['product_name'])
            
            # Escribir valores en las columnas correspondientes
            worksheet.write(row, 0, line['default_code'])  # Referencia (texto)
            worksheet.write(row, 1, name)  # Producto / Empaquetado (texto)
            worksheet.write(row, 2, float(line['units']), number_format)  # CONSUMO REAL (Un.)
            worksheet.write(row, 3, float(line['returned_units']), number_format)  # DEVOLUCION (Un.)
            worksheet.write(row, 4, float(line['return_percentage']), number_format)  # % Devuelto (€)
            worksheet.write(row, 5, float(line['net_weight']), number_format)  # Total Kg neto
            worksheet.write(row, 6, float(line['total_amount_no_tax']), number_format)  # Total Fact. Base
            worksheet.write(row, 7, float(line['total_amount']), number_format)  # Total Fact con IVA

        # Ajustar anchos de columnas
        worksheet.set_column(0, 0, 50)  # Producto / Empaquetado
        worksheet.set_column(1, 1, 15)  # Referencia
        worksheet.set_column(2, 7, 15)  # Columnas numéricas

        workbook.close()
        output.seek(0)

        excel_data = base64.b64encode(output.read())
        output.close()

        attachment = self.env['ir.attachment'].create({
            'name': f'Reporte_Neto_{self.fecha_inicio}_a_{self.fecha_fin}.xlsx',
            'datas': excel_data,
            'type': 'binary',
            'res_model': self._name,
            'res_id': self.id,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }