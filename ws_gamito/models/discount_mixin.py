from odoo import models
import logging
import re

_logger = logging.getLogger(__name__)

class DiscountMixin:

#DESCUENTOS GLOBALES  
    @staticmethod                  
    def is_line_real_or_virtual(line):
        # Verificar si el id es un entero, lo que indica un registro guardado
        if isinstance(line.id, int):
            return "real"
        # Verificar si el id es una instancia de NewId para registros no guardados
        elif isinstance(line.id, models.NewId):
            id_str = str(line.id)
            # Verificar si contiene la palabra "virtual" en la representación de cadena
            if "virtual" in id_str:
                return "virtual"
            else:
                return "newid"
        # Por defecto, considerar cualquier otro caso como desconocido
        else:
            return "unknown"
            
    @staticmethod 
    def update_discount_lines(order):
        # Ordenar las líneas por secuencia u otro criterio apropiado
        sorted_lines = order.order_line.sorted(key=lambda l: l.sequence)


        base_before_discount = 0.0

        for line in sorted_lines:            
            # Si es una línea de descuento, calcular el descuento y actualizarla
            es_real=DiscountMixin.is_line_real_or_virtual(line)=='real'
            _logger.info(f'WSEM itera linea id:{line.id}, name:{line.product_id.name}, base:{base_before_discount}, seq:{line.sequence}. Es real {es_real}')
            subtotal_linea=line.price_subtotal            
            if es_real:
                if line.product_id.name == 'DESCUENTO':                
                    if line.name:                        
                        discount_percentage = DiscountMixin.extract_discount_percentage(line.name)                                
                        if discount_percentage:                                            
                            line.product_uom_qty= 1
                            precio_lin_desc=-(base_before_discount * (discount_percentage / 100.0))
                            line.price_unit= precio_lin_desc
                            subtotal_linea= precio_lin_desc
                            _logger.info(f'WSEM descuento:{subtotal_linea}')
                            
                # Actualizar la base antes de descuento acumulada
                base_before_discount += subtotal_linea
     
    @staticmethod      
    def extract_discount_percentage(description):
        # Extraer el porcentaje de descuento de la descripción, esperando la sintaxis "DESCUENTO X%"
        match = re.search(r'^(?:DESCUENTO\s+)?(\d+(?:\.\d+)?)%', description)
        if match:
            return float(match.group(1))
        return None