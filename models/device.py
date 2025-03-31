from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import ipaddress
import re


class Device(models.Model):
    _name = "network.device"
    _description = "Network Device"
    _order = "ip_integer"

    name = fields.Char(string="Device Name")
    mac_address = fields.Char(string="MAC Address", required=True)
    ip_address = fields.Char(string="IP Address", required=True)
    ip_integer = fields.Integer(
        compute="_compute_ip_integer",
        store=True,
        index=True,
        string="IP Integer",
        help="Numerical representation of the IP for sorting",
    )
    subnet_id = fields.Many2one("network.subnet", string="Subnet", required=True)
    active = fields.Boolean(string="Active", default=True)
    partner_id = fields.Many2one("res.partner", string="Owner", required=True)
    netadmin_id = fields.Integer(string="Netadmin ID")

    _sql_constraints = [
        # (
        #     "unique_mac_subnet",
        #     "unique (mac_address, subnet_id)",
        #     "MAC address must be unique within the subnet!",
        # ),
        (
            "unique_ip_subnet",
            "unique(ip_address, subnet_id)",
            "IP must be unique per subnet!",
        ),
    ]

    @api.depends("ip_address")
    def _compute_ip_integer(self):
        """Convert valid IPv4 address to integer for sorting"""
        for device in self:
            if device.ip_address:
                try:
                    ip = ipaddress.IPv4Address(device.ip_address)
                    device.ip_integer = int(ip)
                except ipaddress.AddressValueError:
                    device.ip_integer = 0
            else:
                device.ip_integer = 0

    @api.constrains("mac_address")
    def _check_mac_format(self):
        for device in self:
            if not re.match(
                r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", device.mac_address.strip()
            ):
                raise ValidationError(
                    _(
                        "Invalid MAC address format. Use formats like 00:1A:2B:3C:4D:5E or 00-1A-2B-3C-4D-5E"
                    )
                )

    @api.constrains("ip_address")
    def _check_ip_format(self):
        for device in self:
            try:
                ipaddress.IPv4Address(device.ip_address)
            except ipaddress.AddressValueError:
                raise ValidationError(_("Invalid IPv4 address format."))

    @api.constrains("ip_address", "subnet_id")
    def _check_ip_in_subnet(self):
        for device in self:
            if device.subnet_id.cidr and device.ip_address:
                try:
                    network = ipaddress.IPv4Network(device.subnet_id.cidr, strict=False)
                    ip = ipaddress.IPv4Address(device.ip_address)
                    if ip not in network:
                        raise ValidationError(
                            _("IP address %s is not within the subnet %s.")
                            % (device.ip_address, device.subnet_id.cidr)
                        )
                except ValueError:
                    pass
