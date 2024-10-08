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
        result = super(IrExports, self).export_data(model, ids, fields, domain, groupby, offset, limit, sort)
        
        if model == 'account.move.line':
            # Actualizar la fecha de exportación para los registros exportados
            records = self.env[model].browse(ids) if ids else self.env[model].search(domain or [])
            records.write({'export_date': fields.Datetime.now()})
        
        return result