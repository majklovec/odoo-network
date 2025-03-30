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
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/subnet_views.xml",  # Load first
        "views/device_views.xml",
        "views/partner_views.xml",
        "views/menu_views.xml",  # Load last
    ],
    "demo": [],
    "installable": True,
    "application": True,
    "auto_install": False,
    "icon": "/network/static/description/icon.png",
    "languages": {
        "cs": "Czech translations",
    },
    "license": "LGPL-3",
}
