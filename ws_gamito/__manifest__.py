# -*- coding: utf-8 -*-
{
    'name': "ws_gamito",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Semantic Web Software SL",
    'website': "https://wsemantic.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '16.0.0.10',

    # any module necessary for this one to work correctly
    'depends': ['account','stock','sale'], 
    'external_dependencies': {'python': ['xlsxwriter']},
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/descuentos.xml',
        'views/templates.xml',
        'views/sale_report_view.xml',
        'views/invoice_report.xml',
        'report/report_deliveryslip_weight.xml',
        'report/stock_picking_operations.xml',
        'report/deliver_from_order.xml',
        'report/report_invoice_net.xml',
        'data/ws_gamito_data.xml',
        'wizard/report_invoice_net_wizard_view.xml'
        
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    "license": "AGPL-3",
}
