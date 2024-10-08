# -*- coding: utf-8 -*-
# from odoo import http


# class Wsem(http.Controller):
#     @http.route('/wsem/wsem', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/wsem/wsem/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('wsem.listing', {
#             'root': '/wsem/wsem',
#             'objects': http.request.env['wsem.wsem'].search([]),
#         })

#     @http.route('/wsem/wsem/objects/<model("wsem.wsem"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('wsem.object', {
#             'object': obj
#         })


# account_due_list_export/controllers/export.py

from odoo.addons.web.controllers import export as export_controller
from odoo.http import request
from odoo import fields

class ExportController(export_controller.Export):

    def index(self, model, fields, ids, **kwargs):
        """
        Sobrescribimos el método de exportación para registrar la fecha de exportación
        """
        # Llamar al método original para realizar la exportación
        res = super(ExportController, self).index(model, fields, ids, **kwargs)

        # Solo registrar la fecha si estamos exportando el modelo account.move.line
        if model == 'account.move.line':
            if ids:
                # Obtener los registros exportados
                records = request.env['account.move.line'].browse(ids)
                # Establecer la fecha de exportación
                records.write({'export_date': fields.Date.today()})

        return res

