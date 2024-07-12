
class SaleOrder(models.Model):
    _inherit = 'sale.order'

#Empresa Test
    @api.onchange('company_id')
    def _onchange_company(self):
        _logger.info("WSEM 1-disparo _onchange_company")
        if self.company_id and self.company_id.name == "Test":            
            new_company_id = self.company_id.id
            _logger.info("WSEM 2- %s ",self.company_id.name)
            for line in self.order_line:
                new_taxes = []
                for tax in line.tax_id:
                    # Buscar un impuesto con el mismo nombre en la nueva compañía
                    new_tax = self.env['account.tax'].search([
                        ('name', '=', tax.name),
                        ('type_tax_use', '=', tax.type_tax_use),
                        ('company_id', '=', new_company_id),
                    ], limit=1)
                    if new_tax:
                        new_taxes.append(new_tax.id)
                # Actualizar los impuestos de la línea con los nuevos impuestos encontrados
                if new_taxes:
                    line.tax_id = [(6, 0, new_taxes)]
            # Buscar y actualizar el almacén si es necesario
            if self.warehouse_id:              
                _logger.info("WSEM 3- Almacen actual %s ",self.warehouse_id.name)            
                # Buscar un almacén en la nueva compañía del mismo tipo
                new_warehouse = self.env['stock.warehouse'].search([
                    ('company_id', '=', new_company_id)
                ], limit=1)
                if new_warehouse:
                    _logger.info("WSEM 4- Almacen nuevo %s ",new_warehouse.name)   
                    self.warehouse_id = new_warehouse.id  
                    
'''
Utilizado para buscar solo productos de tu propia empresa, para soportar que empresa codinesa no encuentra productos 
class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        context = self._context

        # Comprobar si la información de la empresa está disponible en el contexto
        new_args = []
        skip_next = False
        for arg in args:
            if skip_next:
                skip_next = False
                continue
            if arg == '|':
                # Verificar si el siguiente par de argumentos es ['company_id', '=', False]
                if args[args.index(arg) + 1] == ['company_id', '=', False]:
                    skip_next = True
                    continue
            new_args.append(arg)

        # Continuar con la lógica de búsqueda
        #_logger.info('WSEM Argumentos de busqueda ProductProduct en _name_search: %s', new_args)
        return super(ProductProduct, self)._name_search(name, args=new_args, operator=operator, limit=limit, name_get_uid=name_get_uid)
 '''                      