# -*- coding: utf-8 -*-

from . import controllers
from . import models

import logging
_logger = logging.getLogger(__name__)

def set_en_consumo_false(cr, registry):
    with cr.savepoint():
        cr.execute("UPDATE stock_quant SET en_consumo_desde = CURRENT_TIMESTAMP WHERE en_consumo_desde IS NULL;")

def post_init_ws(cr, registry):
    _logger.info("Procesando post init")
    set_en_consumo_false(cr, registry)