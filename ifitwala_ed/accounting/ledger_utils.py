import frappe
from frappe import _
from frappe.utils import flt, getdate


def get_organization_currency(organization):
    return frappe.db.get_value("Organization", organization, "default_currency")


def get_account_currency(account, organization=None):
    currency = frappe.db.get_value("Account", account, "account_currency")
    if currency:
        return currency
    if organization:
        return get_organization_currency(organization)
    return None


def validate_posting_date(organization, posting_date):
    if not (organization and posting_date):
        return

    lock_until_date = frappe.db.get_value("Accounts Settings", organization, "lock_until_date")
    if lock_until_date and getdate(posting_date) <= getdate(lock_until_date):
        frappe.throw(
            _("Posting date {0} is in a locked period for Organization {1}").format(posting_date, organization)
        )

    closed_period = frappe.db.exists(
        "Accounting Period",
        {
            "organization": organization,
            "is_closed": 1,
            "start_date": ["<=", posting_date],
            "end_date": [">=", posting_date],
        },
    )
    if closed_period:
        frappe.throw(_("Posting date {0} falls in a closed Accounting Period").format(posting_date))


def make_gl_entries(entries, voucher_type, voucher_no, cancel=False):
    for entry in entries:
        gl = frappe.new_doc("GL Entry")
        gl.organization = entry["organization"]
        gl.posting_date = entry["posting_date"]
        gl.account = entry["account"]
        gl.party_type = entry.get("party_type")
        gl.party = entry.get("party")
        gl.against = entry.get("against")
        gl.remarks = entry.get("remarks")
        gl.voucher_type = voucher_type
        gl.voucher_no = voucher_no
        gl.is_cancelled = 1 if cancel else 0

        debit = flt(entry.get("debit"))
        credit = flt(entry.get("credit"))
        if cancel:
            debit, credit = credit, debit

        gl.debit = debit
        gl.credit = credit
        gl.account_currency = get_account_currency(gl.account, gl.organization)
        gl.debit_in_account_currency = debit
        gl.credit_in_account_currency = credit
        gl.insert(ignore_permissions=True)


def cancel_gl_entries(voucher_type, voucher_no):
    entries = frappe.get_all(
        "GL Entry",
        filters={"voucher_type": voucher_type, "voucher_no": voucher_no, "is_cancelled": 0},
        fields=[
            "name",
            "organization",
            "posting_date",
            "account",
            "debit",
            "credit",
            "party_type",
            "party",
            "against",
            "remarks",
        ],
    )
    if not entries:
        return

    for entry in entries:
        make_gl_entries(
            [
                {
                    "organization": entry.organization,
                    "posting_date": entry.posting_date,
                    "account": entry.account,
                    "party_type": entry.party_type,
                    "party": entry.party,
                    "against": entry.against,
                    "remarks": entry.remarks,
                    "debit": entry.debit,
                    "credit": entry.credit,
                }
            ],
            voucher_type,
            voucher_no,
            cancel=True,
        )
        frappe.db.set_value("GL Entry", entry.name, "is_cancelled", 1)
