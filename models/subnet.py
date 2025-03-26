from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import ipaddress


class Subnet(models.Model):
    _name = "network.subnet"
    _description = "Network Subnet"

    name = fields.Char(string="Subnet Name", required=True)
    cidr = fields.Char(string="CIDR Block", required=True, help="E.g., 192.168.1.0/24")
    description = fields.Text(string="Description")
    device_ids = fields.One2many("network.device", "subnet_id", string="Devices")
    # external_id = fields.Integer(string="Netadmin ID")

    @api.constrains("cidr")
    def _check_cidr_format(self):
        for subnet in self:
            try:
                ipaddress.IPv4Network(subnet.cidr, strict=False)
            except ValueError:
                raise ValidationError(
                    _("Invalid CIDR format. Use formats like 192.168.1.0/24")
                )
