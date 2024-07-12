from odoo import models
import logging
import re

_logger = logging.getLogger(__name__)

class DiscountMixin:

#DESCUENTOS GLOBALES  
    @staticmethod                  
    def ws_is_desc(line):
        return line.product_id and line.product_id.name == 'DESCUENTO' 

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
    def update_discount_lines(order, discount_line):
        # Ordenar las líneas por secuencia u otro criterio apropiado        

        if hasattr(order, 'order_line'):
            lines = order.order_line
        elif hasattr(order, 'invoice_line_ids'):
            lines = order.invoice_line_ids
        else:
            _logger.warning(f'WSEM No se pudo determinar las líneas del objeto {order}')
            return

        sorted_lines = lines.sorted(key=lambda l: l.sequence)


        base_before_discount = 0.0
        discount_line_updated = False

        for line in sorted_lines:            
            # Si es una línea de descuento, calcular el descuento y actualizarla
            es_real=DiscountMixin.is_line_real_or_virtual(line)=='real'
            _logger.info(f'WSEM itera linea id:{line.id}, name:{line.product_id.name}, base:{base_before_discount}, seq:{line.sequence}. Es real {es_real} size lineas {len(sorted_lines)}')
            subtotal_linea=line.price_subtotal            
            if es_real:
                _logger.info(f'WSEM si es real pro name: {line.product_id.name}')
                updated=DiscountMixin.update_discount_line(line, base_before_discount)
                if updated and discount_line and line == discount_line:
                    discount_line_updated = True
                            
                # Actualizar la base antes de descuento acumulada
                base_before_discount += subtotal_linea
                
        # Si la línea de descuento no se actualizó en sorted_lines, forzar su actualización
        if discount_line and not discount_line_updated:
            DiscountMixin.update_discount_line(discount_line, base_before_discount)
                
    @staticmethod
    def update_discount_line(line, base_before_discount):
        if line.product_id.name == 'DESCUENTO':
            if line.name:
                discount_percentage = DiscountMixin.extract_discount_percentage(line.name)
                _logger.info(f'WSEM descuento Porc {discount_percentage}')
                if discount_percentage:
                    precio_lin_desc = -(base_before_discount * (discount_percentage / 100.0))
                    line.write({
                        'product_uom_qty': 1,
                        'price_unit': precio_lin_desc,
                    })
                    return True
        return False
     
    @staticmethod      
    def extract_discount_percentage(description):
        # Extraer el porcentaje de descuento de la descripción, esperando la sintaxis "DESCUENTO X%"
        match = re.search(r'^(?:\w+\s+)*(\d+(?:\.\d+)?)%\s*(?:\w+\s*)*', description)
        if match:
            return float(match.group(1))
        return None