from odoo import fields, models
from datetime import datetime, timedelta

class AccountPaymentTermLine(models.Model):
    _inherit = 'account.payment.term.line'

    is_annual = fields.Boolean(string='Is Annual', default=False)
    

    def _compute_terms(self, date_ref, currency, company, tax_amount, tax_amount_currency, sign, untaxed_amount, untaxed_amount_currency):
        result = super(AccountPaymentTerm, self)._compute_terms(date_ref, currency, company, tax_amount, tax_amount_currency, sign, untaxed_amount, untaxed_amount_currency)

        for line in self.line_ids:
            if line.is_annual:
                invoice_date = fields.Date.from_string(date_ref)
                annual_date = datetime(invoice_date.year, line.months, line.days)

                if annual_date < invoice_date:
                    annual_date = annual_date.replace(year=annual_date.year + 1)

                result = [(fields.Date.to_string(annual_date), untaxed_amount)]
                break

        return result