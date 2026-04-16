import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr


class Account(Document):
    def autoname(self):
        self.name = get_account_autoname(self.account_number, self.account_name, self.organization)

    def validate(self):
        self.validate_organization()
        self.validate_root_type()
        self.set_report_type()
        self.validate_parent()
        self.validate_account_type()
        self.validate_group()

    def set_report_type(self):
        if self.root_type in ["Asset", "Liability", "Equity"]:
            self.report_type = "Balance Sheet"
        elif self.root_type in ["Income", "Expense"]:
            self.report_type = "Profit and Loss"

    def validate_organization(self):
        if not self.organization:
            frappe.throw(_("Organization is required"))

    def validate_root_type(self):
        if not self.root_type:
            frappe.throw(_("Root Type is required"))

    def validate_parent(self):
        if self.parent_account:
            parent = frappe.get_doc("Account", self.parent_account)

            if not parent:
                frappe.throw(_("Parent account not found"))

            if parent.organization != self.organization:
                frappe.throw(_("Parent account must belong to the same organization"))

            if parent.root_type != self.root_type:
                frappe.throw(_("Root Type must be the same as parent account"))

            if self.name and parent.name == self.name:
                frappe.throw(_("You cannot be your own parent"))

    def validate_account_type(self):
        if not self.account_type:
            return

        if self.account_type in ["Bank", "Cash", "Receivable"]:
            if self.root_type != "Asset":
                frappe.throw(
                    _("Account Type '{account_type}' must have Root Type 'Asset'").format(
                        account_type=self.account_type
                    )
                )

        if self.account_type == "Tax":
            if self.root_type != "Liability":
                frappe.throw(_("Account Type 'Tax' must have Root Type 'Liability'"))

    def validate_group(self):
        # Posting rules enforced at transaction posting time.
        pass


def get_account_autoname(account_number, account_name, organization):
    organization_abbr = cstr(frappe.get_cached_value("Organization", organization, "abbr")).strip()
    account_name = cstr(account_name).strip()
    account_number = cstr(account_number).strip()

    if account_number:
        base_name = f"{account_number} - {account_name}"
    else:
        base_name = account_name

    if organization_abbr:
        return f"{base_name} - {organization_abbr}"

    return base_name


def _get_account_title(account):
    organization = cstr(account.get("organization")).strip()
    account_number = cstr(account.get("account_number")).strip()
    account_name = cstr(account.get("account_name") or account.get("name")).strip()
    if organization:
        organization_abbr = cstr(frappe.get_cached_value("Organization", organization, "abbr")).strip()
        suffix = f" - {organization_abbr}" if organization_abbr else ""
        if suffix and account_name.endswith(suffix):
            account_name = account_name[: -len(suffix)].rstrip()
    if account_number:
        return f"{account_number} - {account_name}"
    return account_name


@frappe.whitelist()
def get_children(doctype, parent=None, organization=None, is_root=False, **kwargs):
    filters = dict(kwargs.get("filters") or {})
    organization = cstr(organization or filters.get("organization")).strip()
    if not organization:
        return []

    if is_root or not parent:
        rows = frappe.get_all(
            "Account",
            filters={"organization": organization},
            fields=["name", "organization", "account_name", "account_number", "parent_account", "is_group"],
            order_by="lft asc",
            limit=5000,
        )
        root_rows = []
        for row in rows:
            if cstr(row.get("parent_account")).strip():
                continue
            root_rows.append(
                {
                    "value": row.get("name"),
                    "title": _get_account_title(row),
                    "expandable": 1 if row.get("is_group") else 0,
                }
            )
        return root_rows

    rows = frappe.get_all(
        "Account",
        filters={"organization": organization, "parent_account": parent},
        fields=["name", "organization", "account_name", "account_number", "is_group"],
        order_by="lft asc",
        limit=5000,
    )
    return [
        {
            "value": row.get("name"),
            "title": _get_account_title(row),
            "expandable": 1 if row.get("is_group") else 0,
        }
        for row in rows
    ]
