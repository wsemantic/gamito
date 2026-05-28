# -*- coding: utf-8 -*-

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _get_name(self):
        """Mostrar el nombre legal primero y el comercial después,
        preservando la lógica del core (show_address, show_vat, etc).

        Nota ruta original (Odoo 16): odoo/addons/base/models/res_partner.py
        """
        name = super()._get_name()
        legal = self.name or ''
        if legal and self.commercial_company_name and self.commercial_company_name != legal:
            name = name.replace(legal, f"{legal} ({self.commercial_company_name})", 1)
        return name
