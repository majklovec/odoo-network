from odoo import models, fields


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _default_payment_reference(self):
        return self.env["ir.sequence"].next_by_code("partner.payment.ref")

    device_ids = fields.One2many("network.device", "partner_id", string="Devices")
    payment_reference_id = fields.Char(
        string="Payment Reference Id", default=_default_payment_reference
    )
    netadmin_id = fields.Integer(string="Netadmin ID")
