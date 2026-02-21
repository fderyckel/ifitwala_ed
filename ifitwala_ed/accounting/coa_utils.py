# ifitwala_ed/accounting/coa_utils.py
import frappe
from frappe import _

from ifitwala_ed.accounting.doctype.account.chart_of_accounts.chart_of_accounts import (
    create_charts,
    get_chart,
)

DEFAULT_CHART_TEMPLATE = "standard_chart_of_accounts"


def get_minimal_coa_skeleton():
    """
    Returns a Python structure describing the minimal required tree.
    """
    return [
        # Assets
        {"account_name": "Assets", "root_type": "Asset", "is_group": 1, "parent": None},
        {
            "account_name": "Accounts Receivable",
            "root_type": "Asset",
            "account_type": "Receivable",
            "is_group": 0,
            "parent": "Assets",
        },
        {
            "account_name": "Cash",
            "root_type": "Asset",
            "account_type": "Cash",
            "is_group": 0,
            "parent": "Assets",
        },
        {
            "account_name": "Bank",
            "root_type": "Asset",
            "account_type": "Bank",
            "is_group": 0,
            "parent": "Assets",
        },
        # Liabilities
        {"account_name": "Liabilities", "root_type": "Liability", "is_group": 1, "parent": None},
        {
            "account_name": "Advances / Unearned Revenue",
            "root_type": "Liability",
            "is_group": 0,
            "parent": "Liabilities",
            "account_type": None,
        },
        {
            "account_name": "Tax Payable",
            "root_type": "Liability",
            "account_type": "Tax",
            "is_group": 0,
            "parent": "Liabilities",
        },
        # Equity
        {"account_name": "Equity", "root_type": "Equity", "is_group": 1, "parent": None},
        # Income
        {"account_name": "Income", "root_type": "Income", "is_group": 1, "parent": None},
        # Expenses
        {"account_name": "Expenses", "root_type": "Expense", "is_group": 1, "parent": None},
    ]


def get_account_by_name(organization, account_name, parent=None):
    """
    Returns IF Account name (docname) for that org + name.
    If parent is specified, we check for exact parent match.
    """
    filters = {"organization": organization, "account_name": account_name}
    if parent:
        filters["parent_account"] = parent

    accounts = frappe.get_all("Account", filters=filters, pluck="name", limit=1)
    return accounts[0] if accounts else None


def get_account_by_type(organization, account_type, root_type=None, prefer_leaf=True):
    filters = {"organization": organization, "account_type": account_type}
    if root_type:
        filters["root_type"] = root_type

    accounts = frappe.get_all(
        "Account",
        filters=filters,
        fields=["name", "is_group"],
        order_by="is_group asc, name asc",
    )

    if prefer_leaf:
        for account in accounts:
            if not account.is_group:
                return account.name

    return accounts[0].name if accounts else None


def get_advance_account(organization):
    accounts = frappe.get_all(
        "Account",
        filters={"organization": organization, "root_type": "Liability"},
        fields=["name", "account_name"],
        order_by="name asc",
    )

    for account in accounts:
        name = (account.account_name or "").lower()
        if "advance" in name or "unearned" in name:
            return account.name

    return None


def _get_root_accounts(organization):
    accounts = frappe.get_all(
        "Account",
        filters={"organization": organization},
        fields=["name", "parent_account"],
    )
    return [account.name for account in accounts if not account.parent_account]


def create_coa_for_organization(organization, template_name=None):
    """
    Creates accounts for the given Organization.
    Must be idempotent.
    Returns dict with stats.
    """
    if not template_name:
        template_name = DEFAULT_CHART_TEMPLATE

    existing_count = frappe.db.count("Account", filters={"organization": organization})
    if existing_count:
        return {
            "created": 0,
            "skipped": existing_count,
            "root_accounts": _get_root_accounts(organization),
        }

    chart = get_chart(template_name)
    if not chart:
        frappe.throw(_("Chart of Accounts template not found: {0}").format(template_name))

    create_charts(organization, custom_chart=chart, chart_template=template_name)

    created_count = frappe.db.count("Account", filters={"organization": organization})
    ensure_accounts_settings(organization)

    return {
        "created": created_count,
        "skipped": 0,
        "root_accounts": _get_root_accounts(organization),
    }


def ensure_accounts_settings(organization):
    """
    Create Accounts Settings for the organization if missing.
    """
    if frappe.db.exists("Accounts Settings", organization):
        return

    defaults = {
        "default_receivable_account": get_account_by_type(organization, "Receivable", root_type="Asset"),
        "default_cash_account": get_account_by_type(organization, "Cash", root_type="Asset"),
        "default_bank_account": get_account_by_type(organization, "Bank", root_type="Asset"),
        "default_tax_payable_account": get_account_by_type(organization, "Tax", root_type="Liability"),
    }
    defaults["default_advance_account"] = get_advance_account(organization)

    missing = [key for key, value in defaults.items() if not value and key != "default_advance_account"]
    if missing:
        frappe.throw(_("Missing default accounts for Accounts Settings: {0}").format(", ".join(missing)))

    settings = frappe.new_doc("Accounts Settings")
    settings.organization = organization
    settings.update({key: value for key, value in defaults.items() if value})
    settings.insert(ignore_permissions=True)
