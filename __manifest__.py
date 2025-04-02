{
    "name": "Network Management",
    "version": "1.0",
    "summary": "Manage network devices and subnets",
    "description": """
        Manage devices and subnets in a network.
        Partners can own multiple devices in different subnets.
    """,
    "category": "Network",
    "author": "Michal Vondráček",
    "website": "https://www.optimal4.cz",
    "depends": ["base", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/network_subnet_views.xml",
        "views/network_device_views.xml",
        "views/res_partner_views.xml",
    ],
    "demo": [],
    "installable": True,
    "application": True,
    "auto_install": False,
    "icon": "/network/static/description/icon.png",
    "external_dependencies": {
        "python": ["pymysql"],
    },
    "languages": {
        "cs": "Czech translations",
    },
    "license": "LGPL-3",
}
