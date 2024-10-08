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
        y actualizar la fecha de exportación solo si hay active_ids.
        """
        # Log inicial
        _logger.info(f'WSEM dentro export')
        
        # Imprimir detalles del dominio o filtrado
        domain = self.env.context.get('domain', [])
        _logger.info(f'WSEM domain en contexto: {domain}')
        
        # Imprimir detalles de search_default si existen
        search_default = self.env.context.get('search_default', {})
        _logger.info(f'WSEM search_default en contexto: {search_default}')

        # Llamamos al método original para realizar la exportación
        res = super(AccountMoveLine, self).export_data(fields_to_export)

        # Revisar si hay `active_ids` en el contexto
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            # Si hay registros seleccionados, logueamos los active_ids y actualizamos solo esos
            _logger.info(f'WSEM hay active_ids: {active_ids}')
            records = self.browse(active_ids)

            # Log del número de registros localizados
            _logger.info(f'WSEM Número de registros localizados para actualizar: {len(records)}')

            # Actualizar la fecha de exportación solo para los registros correspondientes
            records.write({'export_date': fields.Date.today()})
        else:
            # No hay active_ids, no se realizará ninguna acción
            _logger.info('WSEM no hay active_ids, no se realiza ninguna acción')

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
            
   