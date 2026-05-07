from odoo import api, fields, models
from odoo.tools import float_compare
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from calendar import monthrange

import logging
_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    ws_multiplos	= fields.Float('Multiplos', default=1.0)
    wsem_workcenter = fields.Many2one('mrp.workcenter', string='Centro',compute='_compute_wsem_workcenter', store=True)
    wsem_packaging_id = fields.Many2one(
        'product.packaging',
        string='Envasado',
        help='Select the packaging for the production order'
    )
    ws_ordenes= fields.Char(string='Ordenes')  
    ws_fecha_grupo_str = fields.Char(string='Fecha Grupo')
    ws_fecha_min_str = fields.Char(string='Fecha Minima') #fecha minima de entrega de las ordenes de venta agrupadas
    ws_fecha_max_str = fields.Char(string='Fecha Maxima') #fecha maxima de entrega de las ordenes de venta agrupadas
    
    packaging_qty = fields.Float(
        string='Cantidad por bulto',
        related='wsem_packaging_id.qty',
        readonly=True
    )
    
    ws_demanda_minima	= fields.Float('Cantidad demanda', default=1.0)
    ws_bultos	= fields.Float('Bultos', compute='_compute_total_bultos')

    qty_available = fields.Float(
        string='Stock disponible',
        related='product_id.qty_available',
        readonly=True,
        digits=(16, 0)
    )
    
    @api.depends('product_qty', 'packaging_qty')
    def _compute_total_bultos(self):
        for record in self:
            if record.packaging_qty:
                record.ws_bultos = record.product_qty / record.packaging_qty
            else:
                record.ws_bultos = 0
    
    @api.depends('workorder_ids')
    def _compute_wsem_workcenter(self):
        for production in self:
            if production.workorder_ids:
                production.wsem_workcenter = production.workorder_ids[0].workcenter_id
            else:
                production.wsem_workcenter = False
                
    @api.onchange('ws_multiplos')
    def _onchange_ws_multiplos(self):
        if self.state != 'draft':
            return
        if self.ws_multiplos and self.bom_id:
            self.product_qty = self.bom_id.product_qty * self.ws_multiplos

    @api.onchange('product_qty', 'bom_id')
    def _onchange_product_qty(self):
        if self.product_qty and self.bom_id:
            self.ws_multiplos = self.product_qty / self.bom_id.product_qty

    def write(self, vals):
        res = super().write(vals)
        if 'ws_multiplos' in vals:
            for rec in self:
                if rec.state not in ('confirmed', 'progress'):
                    continue
                if not (rec.bom_id and rec.ws_multiplos and rec.bom_id.product_qty):
                    continue
                new_qty = rec.bom_id.product_qty * rec.ws_multiplos
                rounding = rec.product_uom_id.rounding or 0.01
                if float_compare(new_qty, rec.product_qty, precision_rounding=rounding) != 0:
                    self.env['change.production.qty'].create({
                        'mo_id': rec.id,
                        'product_qty': new_qty,
                    }).change_prod_qty()
        if 'date_planned_start' in vals:
            for rec in self:
                if rec.lot_producing_id:
                    rec._refresh_lot_for_production()
        return res
            
    def _is_intermediate_product(self):
        self.ensure_one()
        cat = self.product_id.categ_id
        while cat:
            if cat.name == 'INT (Amasado)':
                return True
            cat = cat.parent_id
        return False

    def _compute_lot_expiration(self, production_date):
        self.ensure_one()
        if self._is_intermediate_product():
            return production_date + relativedelta(months=16)
        if production_date.month <= 6:
            year = production_date.year + 1
            month = production_date.month
            last_day = monthrange(year, month)[1]
            return datetime(year, month, last_day)
        return datetime(production_date.year + 1, 12, 31)

    def _compute_lot_dates(self, production_date):
        self.ensure_one()
        product = self.product_id
        vals = {'expiration_date': self._compute_lot_expiration(production_date)}
        if product.use_time:
            vals['use_date'] = production_date + timedelta(days=product.use_time)
        if product.alert_time:
            vals['alert_date'] = production_date + timedelta(days=product.alert_time)
        if product.removal_time:
            vals['removal_date'] = production_date + timedelta(days=product.removal_time)
        return vals

    def _get_production_local_datetime(self):
        self.ensure_one()
        dt = self.date_planned_start or fields.Datetime.now()
        return fields.Datetime.context_timestamp(self, dt)

    def _lot_is_exclusive_to_self(self, lot):
        self.ensure_one()
        if not lot:
            return False
        other_prod = self.env['mrp.production'].search_count([
            ('lot_producing_id', '=', lot.id),
            ('id', '!=', self.id),
        ])
        if other_prod:
            return False
        if self.env['stock.quant'].search_count([('lot_id', '=', lot.id)]):
            return False
        if self.env['stock.move.line'].search_count([('lot_id', '=', lot.id)]):
            return False
        return True

    def _refresh_lot_for_production(self):
        self.ensure_one()
        if self.product_id.tracking == 'none':
            return self.lot_producing_id

        production_date = self._get_production_local_datetime()
        new_lot_name = production_date.strftime("%g%V%u")
        new_dates = self._compute_lot_dates(production_date)

        target = self.lot_producing_id
        if not target or target.name != new_lot_name:
            target = self.env['stock.lot'].search([
                ('name', '=', new_lot_name),
                ('product_id', '=', self.product_id.id),
            ], limit=1)
            if not target and self.lot_producing_id and self._lot_is_exclusive_to_self(self.lot_producing_id):
                target = self.lot_producing_id

        if not target:
            lot_vals = self._prepare_stock_lot_values()
            lot_vals['name'] = new_lot_name
            lot_vals.update(new_dates)
            target = self.env['stock.lot'].create(lot_vals)
            _logger.info(f'WSEM v2 nuevo lote :{new_lot_name}')
        else:
            updates = {}
            if target.name != new_lot_name:
                updates['name'] = new_lot_name
            for field, val in new_dates.items():
                if target[field] != val:
                    updates[field] = val
            if updates:
                target.write(updates)

        if self.lot_producing_id != target:
            self.lot_producing_id = target
            if self.product_id.tracking == 'serial':
                self._set_qty_producing()

        return target

    def action_generate_serial(self):
        self.ensure_one()
        return self._refresh_lot_for_production()