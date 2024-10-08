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
                
    def export_data(self, fields_to_export):
        """
        Sobrescribimos el método `export_data` para capturar los registros exportados
        y actualizar la fecha de exportación utilizando los registros en `self`.
        """
        # Log inicial
        _logger.info(f'WSEM dentro export')

        # Llamamos al método original para realizar la exportación
        res = super(AccountMoveLine, self).export_data(fields_to_export)

        # Usar los registros en `self` que están siendo exportados
        if self:
            # Log de los registros que se están exportando
            _logger.info(f'WSEM Registros exportados (self): {self.ids}')
            # Log del número de registros localizados
            _logger.info(f'WSEM Número de registros localizados para actualizar: {len(self)}')

            # Actualizar la fecha de exportación solo para los registros en self
            self.write({'export_date': fields.Date.today()})
        else:
            _logger.info('WSEM No se encontraron registros en self para actualizar')

        return res
        



                
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
            
   