from odoo import models, fields, api
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

#removal estrategia least_fifo
class StockQuantCustom(models.Model):
    _inherit = 'stock.quant'
    en_consumo_desde = fields.Datetime(
        'Fecha y hora de inicio de consumo',
        default=fields.Datetime.now(),
        required=True,
    )

    def _get_removal_strategy_order(self, removal_strategy):
        if removal_strategy == 'least_fifo_lot':
            return 'en_consumo_desde DESC, in_date ASC, id'
        return super(StockQuantCustom, self)._get_removal_strategy_order(removal_strategy)
        
class StockMoveCustom(models.Model):
    _inherit = 'stock.move'
    
    @api.onchange('lot_ids')
    def _onchange_lot_ids(self):
        _logger.info(f'WSEM cambio de lote')
        result = super()._onchange_lot_ids()

        quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product_id.id),
            ('lot_id', 'in', self.lot_ids.ids),
            ('quantity', '!=', 0),
            ('location_id', '!=', self.location_id.id),
            # Exclude the source location
            ('|', ('location_id.usage', '=', 'customer'), '&', ('company_id', '=', self.company_id.id), ('location_id.usage', 'in', ('internal', 'transit')))])

        if quants:
            for quant in quants:
                if quant.lot_id == self.lot_ids[-1]:
                    quant.en_consumo_desde = fields.Datetime.now()
                    quant.write({'en_consumo_desde': fields.Datetime.now()})

        return result
        
    def write(self, vals):
        # Si se modifica el campo `lot_ids`
        _logger.info(f'WSEM write de lote')         
        if vals.get('move_line_ids'):
            _logger.info(f'WSEM existe campo move_line_ids')
            for command in vals['move_line_ids']:
                if command[0] == 1:  # 1 indica una actualización
                    _logger.info(f'WSEM dentro de campo move_line_ids')
                    move_line_id = command[1]  # ID de la línea de movimiento
                    update_values = command[2]  # Diccionario de valores a actualizar
                    if 'lot_id' in update_values:
                        # Aquí puedes procesar el nuevo valor de lot_id
                        _logger.info(f'WSEM write de lote IN, lot_id: {update_values["lot_id"]}')                
                        # Buscamos el stock quant del lote
                        lot_id_capturado = update_values["lot_id"]
                        extra_domain = [('lot_id', '=', lot_id_capturado)]
                        product_ids=(self.product_id.id,),
                        location_ids=(self.location_id.id,),
                            
                        stock_quants = self.env['stock.quant']._get_quants_by_products_locations(
                            self.product_id,
                            self.location_id,
                            extra_domain=extra_domain
                        )

                        if stock_quants:
                            _logger.info(f'WSEM localizados stocks quants')
                            for stock_quants_group in stock_quants.values():
                                for stock_quant in stock_quants_group:
                                    stock_quant.en_consumo_desde = fields.Datetime.now()

        # Llamamos al método `write` original
        
        res = super(StockMoveCustom, self).write(vals)


        return res