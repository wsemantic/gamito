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

        headers = [
            'Producto / Empaquetado',
            'Importe Total (Neto)',
            '% Importe Devuelto',
            'Peso Neto Facturado',
            'Unidades'
        ]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        for row, line in enumerate(line_data, start=1):
            name = (f"{line['product_name']} / {line['packaging_name']}"
                    if data['form']['desglosar_empaquetado'] and line['packaging_name']
                    else line['product_name'])
            worksheet.write(row, 0, name)
            worksheet.write(row, 1, float(line['total_amount']))
            worksheet.write(row, 2, float(line['return_percentage']))
            worksheet.write(row, 3, float(line['net_weight']))
            worksheet.write(row, 4, float(line['units']))

        worksheet.set_column(0, 0, 50)
        worksheet.set_column(1, 4, 15)

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