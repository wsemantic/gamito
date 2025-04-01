from odoo import models, fields

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