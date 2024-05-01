from odoo import api, fields, models

import logging
_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    wsem_workcenter = fields.Many2one('mrp.workcenter', string='Centro',compute='_compute_wsem_workcenter', store=True)

    @api.depends('workorder_ids')
    def _compute_wsem_workcenter(self):
        for production in self:
            if production.workorder_ids:
                production.wsem_workcenter = production.workorder_ids[0].workcenter_id
            else:
                production.wsem_workcenter = False