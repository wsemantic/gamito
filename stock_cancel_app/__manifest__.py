# -*- coding: utf-8 -*-

{
    'name': 'Cancel Stock/Cancel Inventory/Cancel Stock Move/Cancel Scrap Order',
    "author": "Edge Technologies",
    'version': '16.0.1.0',
    'live_test_url': "https://youtu.be/p1xTUaXoUR4",
    "images":['static/description/main_screenshot.png'], 
    'summary': 'Cancel inventory cancel stock picking cancel scrap order cancel stock moves delete stock picking delete scrap order delete stock moves cancel warehouse reverse stock move reverse stock picking reverse stock move cancel scrap order cancel picking reset.',
    'description': 'Stock cancel odoo app',
    'license': "OPL-1",
    'depends': ['base','stock','sale_management'],
    'data': [
        'security/security.xml',
        'wizard/view_cancel_delivery_wizard.xml',
        'views/res_company.xml',
        'views/res_config_settings.xml',
        'views/stock_move.xml',
        'views/stock_picking.xml',
        'views/stock_picking_action.xml',
        'views/stock_scarp_action.xml',
        'views/stock_scrap.xml',
    ],
    'installable': True,
    'auto_install': False,
    'price': 12,
    'currency': "EUR",
    'category': 'Warehouse',
}