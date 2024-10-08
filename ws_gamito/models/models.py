import logging

from odoo import models, fields, api
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)
               
        
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    acc_number = fields.Char(string='Account Number', compute='_compute_acc_number', store=True)
    export_date = fields.Date(string='Fecha de Exportación', readonly=True)

    @api.depends('partner_id.bank_ids')
    def _compute_acc_number(self):
        for line in self:
            bank_accounts = line.partner_id.bank_ids
            if bank_accounts:
                line.acc_number = bank_accounts[0].acc_number  # Obtén el primer número de cuenta bancaria
            else:
                line.acc_number = ''
                
class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    @api.model
    def create(self, vals):
        res = super(ResPartnerBank, self).create(vals)
        self._update_account_move_lines(res.partner_id)
        return res

    def write(self, vals):
        res = super(ResPartnerBank, self).write(vals)
        for bank in self:
            self._update_account_move_lines(bank.partner_id)
        return res

    def _update_account_move_lines(self, partner):
        move_lines = self.env['account.move.line'].search([('partner_id', '=', partner.id)])
        for line in move_lines:
            line._compute_acc_number()
            
   
class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def export_report(self, fields_to_export, raw_data=False):
        """
        Intercepta la acción de exportación.
        """
        _logger.info(f"WSEM Iniciando exportación")
        res = super(IrActionsReport, self).export_report(fields_to_export, raw_data=raw_data)

        # Obtener el contexto para identificar qué registros están siendo exportados
        if self.env.context.get('active_model') == 'account.move.line':
            if self.env.context.get('active_ids'):
                # Si se han seleccionado registros
                records = self.env['account.move.line'].browse(self.env.context['active_ids'])
            else:
                # Si no hay selección, utilizar el dominio para obtener los registros
                domain = self.env.context.get('domain', [])
                records = self.env['account.move.line'].search(domain)
                
            # Establecer la fecha de exportación en la fecha actual
            records.write({'export_date': fields.Date.today()})

        return res