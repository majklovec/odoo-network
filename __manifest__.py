{
    "name": "Metropolitan Network Management",
    "version": "1.0",
    "summary": "Manage network devices and subnets",
    "description": """
        Manage devices and subnets in a metropolitan network.
        Partners can own multiple devices in different subnets.
    """,
    "category": "Network",
    "author": "Your Name",
    "website": "https://www.example.com",
    "depends": ["base", "contacts"],
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
    "icon": "static/description/icon.png",
    "languages": {
        "cs": "Czech translations",
    },
}
