import logging

from odoo import models, fields, api
from datetime import datetime, timedelta
_logger = logging.getLogger(__name__)
               
        
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    acc_number = fields.Char(string='Account Number', compute='_compute_acc_number', store=True)
    export_date = fields.Datetime(string='Fecha de Exportación', readonly=True)

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
            

class IrExports(models.Model):
    _inherit = 'ir.exports'

    @api.model
    def export_data(self, model, ids, fields, domain=None, groupby=None, offset=0, limit=False, sort=False):
        _logger.info(f"WSEM Iniciando exportación. Modelo: {model}, IDs: {ids}, Campos: {fields}, Dominio: {domain}")
        
        result = super(IrExports, self).export_data(model, ids, fields, domain, groupby, offset, limit, sort)
        
        _logger.info(f"WSEM Exportación completada. Resultado: {result}")
        
        if model == 'account.move.line':
            _logger.info("El modelo es account.move.line. Actualizando fechas de exportación.")
            
            if ids:
                records = self.env[model].browse(ids)
                _logger.info(f"WSEM Actualizando {len(records)} registros específicos.")
            elif domain:
                records = self.env[model].search(domain)
                _logger.info(f"WSEM Actualizando {len(records)} registros basados en el dominio: {domain}")
            else:
                records = self.env[model].search([])
                _logger.info(f"WSEM Actualizando todos los registros: {len(records)}")
            
            current_time = fields.Datetime.now()
            update_result = records.write({'export_date': current_time})
            
            _logger.info(f"WSEM Actualización de fechas completada. Resultado: {update_result}")
            
            # Verificación adicional
            for record in records:
                if record.export_date != current_time:
                    _logger.warning(f"WSEM La fecha de exportación no se actualizó correctamente para el registro ID {record.id}")
                else:
                    _logger.info(f"WSEM Fecha de exportación actualizada correctamente para el registro ID {record.id}")
        
        return result