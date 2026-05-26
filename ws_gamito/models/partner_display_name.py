# -*- coding: utf-8 -*-

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_name(self):
        """Mostrar el nombre legal primero y el comercial después.

        Nota ruta original (Odoo 16): odoo/addons/base/models/res_partner.py
        """
        name = self.name or ''
        if self.commercial_company_name and self.commercial_company_name != name:
            return f"{name} ({self.commercial_company_name})"
        return name
