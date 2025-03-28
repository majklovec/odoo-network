from odoo import models, fields, api, exceptions, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _default_payment_reference(self):
        return self.env["ir.sequence"].next_by_code("partner.payment.ref")

    device_ids = fields.One2many("network.device", "partner_id", string="Devices")
    payment_reference_id = fields.Char(
        string="Payment Reference Id", default=_default_payment_reference
    )
    netadmin_id = fields.Integer(string="Netadmin ID")
    user_id = fields.Many2one("res.users", string="Linked User")
    login = fields.Char(string="Login", related="user_id.login", readonly=False)

    @api.model
    def create(self, vals_list):
        # Extract login and password from each vals and remove them
        extracted_data = []
        for vals in vals_list:
            login = vals.pop("login", False)
            password = vals.pop("password", False)
            extracted_data.append({"login": login, "password": password})

        # Create partners in batch
        partners = super().create(vals_list)

        # Create users for each partner with extracted data
        for partner, data in zip(partners, extracted_data):
            login = data["login"]
            password = data["password"]
            if login:
                existing_user = self.env["res.users"].search(
                    [("login", "=", login)], limit=1
                )
                if existing_user:
                    raise exceptions.ValidationError(
                        _("Login %s already exists in the system") % login
                    )
                if not password:
                    raise exceptions.ValidationError(
                        _("Password is required when creating a user")
                    )
                user_vals = {
                    "login": login,
                    "password": password,
                    "partner_id": partner.id,
                    "groups_id": [(6, 0, [])],
                }
                user = self.env["res.users"].create(user_vals)
                partner.user_id = user.id

        return partners

    def write(self, vals):
        if "login" in vals:
            new_login = vals["login"]
            password = vals.pop("password", False)
            for partner in self:
                if partner.user_id:
                    existing_user = self.env["res.users"].search(
                        [("login", "=", new_login), ("id", "!=", partner.user_id.id)],
                        limit=1,
                    )
                    if existing_user:
                        raise exceptions.ValidationError(
                            _("Login %s already exists in the system") % new_login
                        )
                    update_vals = {"login": new_login}
                    if password:
                        update_vals["password"] = password
                    partner.user_id.write(update_vals)
                else:
                    if not password:
                        raise exceptions.ValidationError(
                            _("Password is required when creating a user")
                        )
                    user_vals = {
                        "login": new_login,
                        "password": password,
                        "partner_id": partner.id,
                        "groups_id": [(6, 0, [])],
                    }
                    user = self.env["res.users"].create(user_vals)
                    partner.user_id = user.id
        return super().write(vals)
