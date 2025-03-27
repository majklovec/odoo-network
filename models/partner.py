from odoo import models, fields, api, exceptions, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Existing fields
    def _default_payment_reference(self):
        return self.env["ir.sequence"].next_by_code("partner.payment.ref")

    device_ids = fields.One2many("network.device", "partner_id", string="Devices")
    payment_reference_id = fields.Char(
        string="Payment Reference Id", default=_default_payment_reference
    )
    netadmin_id = fields.Integer(string="Netadmin ID")

    # New fields for user management
    user_id = fields.Many2one("res.users", string="Linked User")
    login = fields.Char(string="Login", related="user_id.login", readonly=False)

    @api.model
    def create(self, vals):
        # Extract user credentials from vals
        login = vals.pop("login", False)
        password = vals.pop("password", False)  # Should be passed via RPC

        # Create partner first
        partner = super().create(vals)

        if login:
            # Check for existing user with same login
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

            # Create user with extracted credentials
            user_vals = {
                "login": login,
                "password": password,
                "partner_id": partner.id,
                "groups_id": [(6, 0, [])],  # Add default groups if needed
            }
            user = self.env["res.users"].create(user_vals)
            partner.user_id = user.id

        return partner

    def write(self, vals):
        # Handle login updates
        if "login" in vals:
            new_login = vals["login"]
            password = vals.pop("password", False)

            for partner in self:
                if partner.user_id:
                    # Check for login uniqueness
                    existing_user = self.env["res.users"].search(
                        [("login", "=", new_login), ("id", "!=", partner.user_id.id)],
                        limit=1,
                    )
                    if existing_user:
                        raise exceptions.ValidationError(
                            _("Login %s already exists in the system") % new_login
                        )

                    # Update existing user
                    update_vals = {"login": new_login}
                    if password:
                        update_vals["password"] = password
                    partner.user_id.write(update_vals)
                else:
                    # Create new user if none exists
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
