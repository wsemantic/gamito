# -*- coding: utf-8 -*-
{
    'name': "mrp_grouping",

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
    'version': '16.0.0.3',

    'post_init_hook': 'post_init_ws',
    
    # any module necessary for this one to work correctly
    'depends': ['stock','sale','mrp','sale_stock'], 

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/mrp_production_views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    "license": "AGPL-3",
}
