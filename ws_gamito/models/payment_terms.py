import logging
from odoo import fields, models
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class AccountPaymentTermLine(models.Model):
    _inherit = "account.payment.term.line"

    is_annual = fields.Boolean(string='Is Annual', default=False)
    
class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"   
    

    def _compute_terms(self, date_ref, currency, company, tax_amount, tax_amount_currency, sign, untaxed_amount, untaxed_amount_currency):
        _logger.info(f'WSEM Entra compute terms')
        result = super(AccountPaymentTerm, self)._compute_terms(date_ref, currency, company, tax_amount, tax_amount_currency, sign, untaxed_amount, untaxed_amount_currency)

        for line in self.line_ids:
            _logger.info(f'WSEM itera linea')
            if line.is_annual:
                _logger.info(f'WSEM es anual')
                for term in result:
                    invoice_date = fields.Date.from_string(date_ref)
                    invoice_datetime = datetime.combine(invoice_date, datetime.min.time())
                    annual_date = datetime(invoice_datetime.year, line.months, line.days)

                    if annual_date < invoice_datetime:
                        annual_date = annual_date.replace(year=annual_date.year + 1)

                    term['date'] = fields.Date.to_string(annual_date)
                break

        return result