import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, cstr, now_datetime, pretty_date

from ifitwala_ed.utilities.employee_utils import get_descendant_organizations, get_user_base_org

ACCOUNT_SCOPE_ROLES = {"Accounts Manager", "Accounts User"}
ACCOUNT_READ_PTYPES = {"read", "report", "select"}


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


@frappe.whitelist()
def get_account_name_number_update_preview(name, account_name, account_number=None):
    name = cstr(name).strip()
    account_name = cstr(account_name).strip()
    account_number = cstr(account_number).strip()

    account = frappe.get_doc("Account", name)
    if not frappe.has_permission("Account", ptype="write", doc=account):
        frappe.throw(_("You are not permitted to update this account."), frappe.PermissionError)

    _validate_account_rename_role()
    _validate_account_can_be_renamed(account)

    if not account_name:
        return {"name": ""}

    return {"name": get_account_autoname(account_number, account_name, account.organization)}


@frappe.whitelist()
def update_account_name_number(name, account_name, account_number=None, reason=None):
    name = cstr(name).strip()
    account_name = cstr(account_name).strip()
    account_number = cstr(account_number).strip()
    reason = cstr(reason).strip()

    if not reason:
        frappe.throw(_("Reason is required to update an account name or number."))
    if not account_name:
        frappe.throw(_("Account Name is required"))

    account = frappe.get_doc("Account", name)
    if not frappe.has_permission("Account", ptype="write", doc=account):
        frappe.throw(_("You are not permitted to update this account."), frappe.PermissionError)

    _validate_account_rename_role()
    _validate_account_can_be_renamed(account)
    _validate_account_number_available(account, account_number)

    old_docname = account.name
    old_account_name = cstr(account.account_name).strip()
    old_account_number = cstr(account.account_number).strip()
    new_docname = get_account_autoname(account_number, account_name, account.organization)
    _validate_account_docname_available(account, new_docname)

    if old_docname == new_docname and old_account_name == account_name and old_account_number == account_number:
        return {"name": old_docname, "audit_comment": None}

    _ensure_account_rename_idle_system()

    frappe.db.set_value("Account", old_docname, "account_number", account_number, update_modified=True)
    frappe.db.set_value("Account", old_docname, "account_name", account_name, update_modified=True)

    if old_docname != new_docname:
        frappe.rename_doc("Account", old_docname, new_docname, force=1)
        frappe.db.set_value("Account", new_docname, "account_name", account_name, update_modified=False)
        frappe.db.set_value("Account", new_docname, "account_number", account_number, update_modified=False)

    audit_comment = _add_account_rename_audit_comment(
        new_docname,
        old_docname=old_docname,
        new_docname=new_docname,
        old_account_name=old_account_name,
        new_account_name=account_name,
        old_account_number=old_account_number,
        new_account_number=account_number,
        reason=reason,
    )
    return {"name": new_docname, "audit_comment": getattr(audit_comment, "name", None)}


def _validate_account_rename_role():
    roles = set(frappe.get_roles() or [])
    if roles & {"Accounts Manager", "System Manager"}:
        return
    frappe.throw(_("Only Accounts Manager or System Manager can update account names or numbers."))


def _validate_account_can_be_renamed(account):
    if not cstr(account.parent_account).strip():
        frappe.throw(_("Root accounts cannot be renamed. Rename a child account instead."))


def _validate_account_number_available(account, account_number):
    if not account_number:
        return

    duplicate = frappe.db.get_value(
        "Account",
        {
            "organization": account.organization,
            "account_number": account_number,
            "name": ["!=", account.name],
        },
        "name",
    )
    if duplicate:
        frappe.throw(
            _("Account Number {account_number} is already used by account {account}.").format(
                account_number=frappe.bold(account_number),
                account=frappe.bold(duplicate),
            )
        )


def _validate_account_docname_available(account, new_docname):
    if new_docname == account.name:
        return
    if frappe.db.exists("Account", new_docname):
        frappe.throw(
            _("Account {account} already exists. Choose a different account name or number.").format(
                account=frappe.bold(new_docname)
            )
        )


def _add_account_rename_audit_comment(account_name, **details):
    account = frappe.get_doc("Account", account_name)
    text = _(
        "Account name/number updated by {user} on {timestamp}. Document name: {old_docname} -> {new_docname}. Account name: {old_account_name} -> {new_account_name}. Account number: {old_account_number} -> {new_account_number}. Reason: {reason}"
    ).format(
        user=frappe.bold(frappe.session.user),
        timestamp=now_datetime(),
        old_docname=frappe.bold(details["old_docname"]),
        new_docname=frappe.bold(details["new_docname"]),
        old_account_name=frappe.bold(details["old_account_name"] or _("Not set")),
        new_account_name=frappe.bold(details["new_account_name"] or _("Not set")),
        old_account_number=frappe.bold(details["old_account_number"] or _("Not set")),
        new_account_number=frappe.bold(details["new_account_number"] or _("Not set")),
        reason=frappe.bold(details["reason"]),
    )
    return account.add_comment("Info", text=text)


def _ensure_account_rename_idle_system():
    if getattr(frappe, "in_test", False):
        return

    try:
        last_gl_update = frappe.db.get_value("GL Entry", {}, "modified", for_update=True, wait=False)
    except frappe.QueryTimeoutError:
        last_gl_update = add_to_date(None, seconds=-1)

    if not last_gl_update:
        return

    if last_gl_update > add_to_date(None, minutes=-5):
        frappe.throw(
            _(
                "Last GL Entry update was done {last_update}. Account names and numbers cannot be updated while accounting activity is in progress. Please wait for 5 minutes before retrying."
            ).format(last_update=pretty_date(last_gl_update)),
            title=_("System In Use"),
        )


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


def _is_unrestricted_account_user(user: str) -> bool:
    if user == "Administrator":
        return True
    return "System Manager" in set(frappe.get_roles(user) or [])


def _has_account_scope_role(user: str) -> bool:
    return bool(set(frappe.get_roles(user) or []) & ACCOUNT_SCOPE_ROLES)


def _get_account_base_organization(user: str) -> str | None:
    return cstr(get_user_base_org(user)).strip() or None


def _get_account_organization_scope_for_base(
    user: str,
    base_organization: str | None,
) -> list[str] | None:
    if _is_unrestricted_account_user(user):
        return None
    if not _has_account_scope_role(user):
        return []

    base_organization = cstr(base_organization).strip()
    if not base_organization:
        return []

    return list(dict.fromkeys(get_descendant_organizations(base_organization) or [base_organization]))


def _get_account_organization_scope(user: str) -> list[str] | None:
    return _get_account_organization_scope_for_base(user, _get_account_base_organization(user))


def _account_user_can_access_organization(user: str, organization: str) -> bool:
    organization = cstr(organization).strip()
    if not organization:
        return False

    scope = _get_account_organization_scope(user)
    if scope is None:
        return True

    return organization in set(scope)


def _get_account_permission_organization(doc, ptype: str | None = None) -> str | None:
    if not doc:
        return None

    ptype = cstr(ptype or "read").strip().lower()
    if hasattr(doc, "get"):
        organization = cstr(doc.get("organization")).strip()
    else:
        organization = cstr(getattr(doc, "organization", "")).strip()
    if organization:
        return organization

    parent_account = cstr(
        doc.get("parent_account") if hasattr(doc, "get") else getattr(doc, "parent_account", "")
    ).strip()
    if ptype == "create" and parent_account:
        parent_organization = frappe.db.get_value("Account", parent_account, "organization")
        return cstr(parent_organization).strip() or None

    account_name = cstr(doc if isinstance(doc, str) else getattr(doc, "name", "")).strip()
    if account_name and frappe.db.exists("Account", account_name):
        account_organization = frappe.db.get_value("Account", account_name, "organization")
        return cstr(account_organization).strip() or None

    return None


def get_permission_query_conditions(user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return "1=0"

    scope = _get_account_organization_scope(user)
    if scope is None:
        return None
    if not scope:
        return "1=0"

    values = ", ".join(frappe.db.escape(organization) for organization in sorted(set(scope)))
    return f"`tabAccount`.`organization` IN ({values})"


def has_permission(doc, ptype=None, user=None):
    user = user or frappe.session.user
    if not user or user == "Guest":
        return False
    if _is_unrestricted_account_user(user):
        return True

    ptype = cstr(ptype or "read").strip().lower()
    roles = set(frappe.get_roles(user) or [])
    if not roles & ACCOUNT_SCOPE_ROLES:
        return False
    if "Accounts Manager" not in roles and ptype not in ACCOUNT_READ_PTYPES:
        return False

    scope = _get_account_organization_scope(user)
    if not scope:
        return False
    if not doc:
        return True

    organization = _get_account_permission_organization(doc, ptype=ptype)
    if not organization:
        return False

    return organization in set(scope)


@frappe.whitelist()
def get_account_tree_context():
    user = frappe.session.user
    if not user or user == "Guest":
        return {
            "default_organization": None,
            "allowed_organizations": [],
            "unrestricted": False,
            "has_scope": False,
            "message": _("Sign in with an accounting user to view the Chart of Accounts."),
        }

    if not _is_unrestricted_account_user(user) and not _has_account_scope_role(user):
        return {
            "default_organization": None,
            "allowed_organizations": [],
            "unrestricted": False,
            "has_scope": False,
            "message": _(
                "Ask an administrator for Accounts User or Accounts Manager access to view the Chart of Accounts."
            ),
        }

    base_organization = _get_account_base_organization(user)
    scope = _get_account_organization_scope_for_base(user, base_organization)
    if scope is None:
        return {
            "default_organization": base_organization,
            "allowed_organizations": [],
            "unrestricted": True,
            "has_scope": True,
            "message": None,
        }

    if not scope:
        return {
            "default_organization": None,
            "allowed_organizations": [],
            "unrestricted": False,
            "has_scope": False,
            "message": _("Set an Organization on your active Employee record before opening the Chart of Accounts."),
        }

    return {
        "default_organization": base_organization if base_organization in scope else scope[0],
        "allowed_organizations": scope,
        "unrestricted": False,
        "has_scope": True,
        "message": None,
    }


@frappe.whitelist()
def get_children(doctype, parent=None, organization=None, is_root=False, **kwargs):
    filters = dict(kwargs.get("filters") or {})
    organization = cstr(organization or filters.get("organization")).strip()
    if not organization:
        return []

    if not _account_user_can_access_organization(frappe.session.user, organization):
        frappe.throw(
            _("You can only view accounts for your Employee Organization and its child Organizations."),
            frappe.PermissionError,
        )

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
