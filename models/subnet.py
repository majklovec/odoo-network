from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import ipaddress


class Subnet(models.Model):
    _name = "network.subnet"
    _description = "Network Subnet"
    _order = "cidr_integer"

    name = fields.Char(string="Subnet Name", required=True)
    cidr = fields.Char(string="CIDR Block", required=True, help="E.g., 192.168.1.0/24")
    cidr_integer = fields.Integer(
        compute="_compute_cidr_integer",
        store=True,
        index=True,
        string="CIDR Integer",
        help="Numerical representation of the CIDR for sorting",
    )
    filter = fields.Selection(
        selection=[("0", "do not filter"), ("1", "macguard"), ("2", "macguard ng")],
        string="Filter Type",
        default=0,
        help="Select the filtering mechanism for this subnet",
    )
    device_ids = fields.One2many("network.device", "subnet_id", string="Devices")
    router_id = fields.Many2one("network.device", string="Router", required=False)
    netadmin_id = fields.Integer(string="Netadmin ID")

    @api.constrains("cidr")
    def _check_cidr_format(self):
        for subnet in self:
            try:
                ipaddress.IPv4Network(subnet.cidr, strict=False)
            except ValueError:
                raise ValidationError(
                    _("Invalid CIDR format. Use formats like 192.168.1.0/24")
                )

    @api.depends("cidr")
    def _compute_cidr_integer(self):
        """Convert valid IPv4 cudr to integer for sorting"""
        for subnet in self:
            if subnet.cidr:
                try:
                    cidr = ipaddress.IPv4Network(subnet.cidr, strict=False)
                    subnet.cidr_integer = int(cidr.network_address)
                except ipaddress.AddressValueError:
                    subnet.cidr_integer = 0
            else:
                subnet.cidr_integer = 0
