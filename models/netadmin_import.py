from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import pymysql
import ipaddress
import re
from .czech_banks import get_banks

_logger = logging.getLogger(__name__)


class NetworkImport(models.Model):
    _name = "network.import"
    _description = "Netadmin Network Data Import"

    def action_import(self):
        """Main import controller"""
        try:
            mysql_data = self._load_mysql_data()
            self._import_core_data(mysql_data)
            return self._success_response()
        except Exception as e:
            self.env.cr.rollback()
            raise UserError(_("Import Error: %s") % str(e))

    def _load_mysql_data(self):
        """Load all MySQL data with proper resource handling"""
        config = {
            "host": "192.168.1.136",
            "port": 23306,
            "user": "majkl",
            "password": "iengeFeeliesh2Hene0jie1Eijeohahr",
            "database": "netadmin",
            "cursorclass": pymysql.cursors.DictCursor,
        }

        try:
            connection = pymysql.connect(**config)
            with connection.cursor() as cursor:
                return {
                    "ciselnik": self._fetch_ciselnik(cursor),
                    "users": self._fetch_users(cursor),
                    "subnets": self._fetch_subnets(cursor),
                    "devices": self._fetch_devices(cursor),
                }
        finally:
            if "connection" in locals():
                connection.close()
                _logger.info("MySQL connection closed")

    def _fetch_ciselnik(self, cursor):
        cursor.execute("SELECT name_cs, value FROM ciselnik WHERE group_id = 1")
        return cursor.fetchall()

    def _fetch_users(self, cursor):
        cursor.execute(
            """SELECT users.id, jmeno, prijmeni, login, bankovni_ucet, email,
                        adresa, mesto, psc, telefon, datum_prijeti, vs, 
                        ciselnik.name_cs, ciselnik.value as status_value
                     FROM users 
                     LEFT JOIN ciselnik ON status = ciselnik.value 
                     WHERE ciselnik.group_id = 1"""
        )
        return cursor.fetchall()

    def _fetch_subnets(self, cursor):
        cursor.execute("SELECT id, name, net_ip, net_mask, router FROM subnets")
        return cursor.fetchall()

    def _fetch_devices(self, cursor):
        cursor.execute("SELECT id, hostname, mac, ip, sid, owner FROM computers")
        return cursor.fetchall()

    def _import_core_data(self, mysql_data):
        """Orchestrate data import sequence"""
        self.import_banks()
        self.env.cr.commit()

        category_map = self.import_ciselnik(mysql_data["ciselnik"])
        self.env.cr.commit()

        user_map = self.import_users(mysql_data["users"], category_map)
        self.env.cr.commit()

        subnet_data = self.import_subnets(mysql_data["subnets"])
        self.env.cr.commit()

        device_result = self.import_devices(
            mysql_data["devices"], user_map, subnet_data["subnet_map"]
        )
        self.env.cr.commit()

        self.update_subnet_routers(
            subnet_data["router_map"], device_result["device_map"]
        )
        self.env.cr.commit()

        if device_result["errors"]:
            self._handle_import_errors(device_result["errors"])

    def import_banks(self):
        """Create/update bank records from CZ_BANK_CODES"""
        Bank = self.env["res.bank"]
        for code, name in get_banks().items():
            bank = Bank.search([("bic", "=", code)], limit=1)
            if not bank:
                Bank.create({"name": name, "bic": code})
                _logger.info("Created bank: %s (%s)", name, code)

    def import_ciselnik(self, ciselnik_data):
        """Handle partner categories"""
        category_map = {}
        Category = self.env["res.partner.category"]

        for item in ciselnik_data:
            name = "Členství / " + item["name_cs"]
            category = Category.search([("name", "=", name)], limit=1)
            if not category:
                category = Category.create({"name": name})
            category_map[item["value"]] = category.id
        return category_map

    def import_users(self, users, category_map):
        """Process user partners with bank accounts"""
        Partner = self.env["res.partner"]
        existing_partners = Partner.search(
            [("netadmin_id", "in", [u["id"] for u in users])]
        )
        partner_map = {p.netadmin_id: p for p in existing_partners}
        country_id = (
            self.env["res.country"].search([("name", "=", "Czech republic")]).id
        )

        for user in users:
            partner = partner_map.get(user["id"])
            try:
                vals = self._prepare_partner_vals(user, country_id, category_map)
                if partner:
                    self._update_existing_partner(partner, vals)
                else:
                    partner = self._create_new_partner(vals)
                partner_map[user["id"]] = partner.id
            except Exception as e:
                _logger.error("User error %s: %s", user["login"], str(e))
        return partner_map

    def _update_existing_partner(self, partner, vals):
        """Handle partner updates with special field handling"""
        # Remove create_date for existing records
        vals.pop("create_date", None)
        partner.write(vals)
        return partner

    def _create_new_partner(self, vals):
        """Create new partner with validation"""
        if not vals.get("name"):
            raise UserError(_("Partner must have a name"))
        return self.env["res.partner"].create(vals)

    def _prepare_partner_vals(self, user, country_id, category_map):
        """Build partner values dictionary"""
        return {
            "name": f"{user['prijmeni']} {user['jmeno']}",
            "email": user["email"],
            "street": user["adresa"],
            "city": user["mesto"],
            "zip": user["psc"],
            "phone": user["telefon"],
            "create_date": user["datum_prijeti"],
            "payment_reference_id": user["vs"],
            "netadmin_id": user["id"],
            "company_type": "person",
            "country_id": country_id,
            "category_id": [(4, category_map[user["status_value"]])],
            "bank_ids": self._prepare_bank_commands(user),
        }

    def _prepare_bank_commands(self, user):
        """Handle bank account creation commands"""
        if not user["bankovni_ucet"]:
            return []

        account_number, bank_id = self._process_bank_account(user["bankovni_ucet"])
        return [(4, 0, {"acc_number": account_number, "bank_id": bank_id})]

    def _process_bank_account(self, bank_account):
        """Split account number and find bank"""
        if "/" not in bank_account:
            return bank_account, False

        acc_number, bank_code = bank_account.split("/", 1)
        bank = self.env["res.bank"].search([("bic", "=", bank_code.strip())], limit=1)
        return acc_number, bank.id if bank else False

    def import_subnets(self, subnets):
        """Handle subnets with router tracking"""
        Subnet = self.env["network.subnet"]
        existing = Subnet.search([("netadmin_id", "in", [s["id"] for s in subnets])])
        subnet_map = {}
        router_map = {}

        for subnet in subnets:
            try:
                record = existing.filtered(lambda s: s.netadmin_id == subnet["id"])
                vals = {
                    "name": subnet["name"],
                    "cidr": self.ip_and_netmask_to_cidr(
                        subnet["net_ip"], subnet["net_mask"]
                    ),
                    "netadmin_id": subnet["id"],
                }

                if record:
                    record.write(vals)
                else:
                    record = Subnet.create(vals)

                subnet_map[subnet["id"]] = record.id
                if subnet.get("router"):
                    router_map[record.id] = subnet["router"]
            except Exception as e:
                _logger.error("Subnet error: %s", str(e))

        return {"subnet_map": subnet_map, "router_map": router_map}

    def import_devices(self, devices, user_map, subnet_map):
        """Process network devices with detailed error tracking"""
        Device = self.env["network.device"]
        existing = Device.search([("netadmin_id", "in", [d["id"] for d in devices])])
        device_map = {}
        errors = []

        for device in devices:
            try:
                # Validate relations before processing
                subnet_id = subnet_map.get(device["sid"])
                partner_id = user_map.get(device["owner"])

                missing = []
                if not subnet_id:
                    missing.append(f"Subnet ID {device['sid']}")
                if not partner_id:
                    missing.append(f"User ID {device['owner']}")

                if missing:
                    raise ValueError(f"Missing relations: {', '.join(missing)}")

                # Proceed with device creation/update
                record = existing.filtered(lambda d: d.netadmin_id == device["id"])
                vals = {
                    "name": device["hostname"],
                    "subnet_id": subnet_id,
                    "partner_id": partner_id,
                    "mac_address": self.fix_mac(device["mac"], device["ip"]),
                    "ip_address": device["ip"],
                    "netadmin_id": device["id"],
                }

                if record:
                    record.write(vals)
                else:
                    record = Device.create(vals)

                device_map[device["id"]] = record.id

            except Exception as e:
                errors.append(
                    {
                        "device": device,
                        "error": f"{device['hostname']}: {str(e)}",
                        "details": {
                            "subnet_id": device["sid"],
                            "user_id": device["owner"],
                            "ip": device["ip"],
                        },
                    }
                )
                _logger.error(
                    "Device import failed: %s",
                    str(e),
                    extra={"device_id": device["id"], "hostname": device["hostname"]},
                )

        return {"device_map": device_map, "errors": errors}

    def update_subnet_routers(self, router_map, device_map):
        """Update subnet router references"""
        updated = 0
        for subnet_id, router_id in router_map.items():
            device_id = device_map.get(router_id)
            if device_id:
                self.env["network.subnet"].browse(subnet_id).write(
                    {"router_id": device_id}
                )
                updated += 1
        _logger.info("Updated routers for %d subnets", updated)

    def _handle_import_errors(self, errors):
        """Generate detailed error report"""
        error_lines = []
        for error in errors:
            line = f"Device {error['device']['hostname']}: {error['error']}"
            line += f"\n  IP: {error['details']['ip']}"
            line += f"\n  Subnet ID: {error['details']['subnet_id']}"
            line += f"\n  Owner ID: {error['details']['user_id']}\n"
            error_lines.append(line)

        raise UserError(
            _(
                "Some devices failed to import:\n\n%s\n"
                "Please check:\n"
                "1. Subnet IDs exist in network.subnet\n"
                "2. Owner IDs exist in res.partner\n"
                "3. IP addresses are properly formatted"
            )
            % "\n".join(error_lines)
        )

    def _success_response(self):
        return {
            "effect": {
                "type": "rainbow_man",
                "message": _("Import completed successfully!"),
            }
        }

    def ip_and_netmask_to_cidr(self, ip, netmask):
        """Convert IP and netmask to CIDR notation"""
        try:
            return str(
                ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False).with_prefixlen
            )
        except ValueError as e:
            raise UserError(_("Invalid IP/Netmask: %s") % str(e))

    def fix_mac(self, mac, ip):
        """Normalize MAC address format or generate from IP if invalid"""
        mac = (mac or "").strip().lower()
        if not mac or mac in ["00:00:00:00:00:00", "00-00-00-00-00-00"]:
            octets = ip.split(".")[-2:]
            return (
                f"02:00:00:{int(octets[0]):02x}:{int(octets[1]):02x}:00"
                if len(octets) == 2
                else "00:00:00:00:00:00"
            )
        mac = re.sub(r"[^a-f0-9]", "", mac)
        return (
            ":".join(mac[i : i + 2] for i in range(0, 12, 2)) if len(mac) == 12 else mac
        )
