# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, now_datetime

from ifitwala_ed.accounting.ledger_utils import cancel_gl_entries, make_gl_entries, validate_posting_date
from ifitwala_ed.accounting.receivables import clamp_money, is_zero, money
from ifitwala_ed.utilities.employee_utils import get_descendant_organizations, get_user_base_org, get_user_base_school
from ifitwala_ed.utilities.school_tree import get_descendant_schools

EXPENSE_CLAIM_CATEGORIES = (
    "Meals",
    "Travel",
    "Transport",
    "Classroom Supplies",
    "Learning Materials",
    "Professional Development",
    "Communication",
    "Accommodation",
    "Other",
)
EXPENSE_CLAIM_STATUSES = {
    "Draft",
    "Submitted",
    "Needs Info",
    "Approved",
    "Rejected",
    "Finance Review",
    "Payable Posted",
    "Paid",
    "Cancelled",
}
EXPENSE_CLAIM_LOCKED_STATUSES = {
    "Submitted",
    "Approved",
    "Rejected",
    "Finance Review",
    "Payable Posted",
    "Paid",
    "Cancelled",
}
EXPENSE_APPROVAL_OVERRIDE_ROLES = {"HR Manager", "HR User", "Academic Admin", "System Manager"}
EXPENSE_FINANCE_ROLES = {"Accounts Manager", "Accounts User", "System Manager"}
EXPENSE_FINANCE_TODO_ROLES = {"Accounts Manager", "Accounts User"}
EXPENSE_STAFF_PORTAL_ROLES = {
    "Employee",
    "Academic Staff",
    "Instructor",
    "HR User",
    "HR Manager",
    "Academic Admin",
    "System Manager",
}

EXPENSE_CLAIM_TODO_MARKER = "[ifitwala:expense_claim]"
EXPENSE_CLAIM_TODO_APPROVER_REVIEW = "approver_review"
EXPENSE_CLAIM_TODO_CLAIMANT_UPDATE = "claimant_update"
EXPENSE_CLAIM_TODO_FINANCE_POST = "finance_post"
EXPENSE_CLAIM_TODO_FINANCE_PAY = "finance_pay"

EXPENSE_CLAIM_FIELDS = [
    "name",
    "employee",
    "employee_name",
    "organization",
    "school",
    "department",
    "claim_title",
    "claim_date",
    "currency",
    "expense_approver",
    "purpose",
    "claimed_total",
    "sanctioned_total",
    "status",
    "submitted_by",
    "submitted_on",
    "decision_by",
    "decision_on",
    "decision_notes",
    "payable_account",
    "payable_posted_by",
    "payable_posted_on",
    "paid_amount",
    "outstanding_amount",
    "payment_entry",
    "paid_on",
    "remarks",
    "modified",
]


def _clean_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _get_roles(user: str | None = None) -> set[str]:
    return set(frappe.get_roles(user or frappe.session.user))


def _is_administrator(user: str | None) -> bool:
    return (user or frappe.session.user) == "Administrator"


def _get_org_scope(user: str | None = None) -> list[str]:
    user = user or frappe.session.user
    if _is_administrator(user) or "System Manager" in _get_roles(user):
        return []
    base_org = get_user_base_org(user)
    if not base_org:
        return []
    return get_descendant_organizations(base_org) or []


def _get_school_scope(user: str | None = None) -> list[str]:
    user = user or frappe.session.user
    if _is_administrator(user) or "System Manager" in _get_roles(user):
        return []
    base_school = get_user_base_school(user)
    if not base_school:
        return []
    return get_descendant_schools(base_school) or [base_school]


def get_current_employee(user: str | None = None) -> dict[str, Any]:
    user = user or frappe.session.user
    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user, "employment_status": ["in", ["Active", "Temporary Leave"]]},
        [
            "name",
            "user_id",
            "employee_full_name",
            "organization",
            "school",
            "department",
            "expense_approver",
        ],
        as_dict=True,
    )
    if not employee:
        frappe.throw(_("An active employee record is required for Expense Claims."), frappe.PermissionError)
    return dict(employee)


def _validate_school_organization(school: str | None, organization: str | None) -> None:
    if not school or not organization:
        return

    school_org = frappe.db.get_value("School", school, "organization")
    if school_org != organization:
        frappe.throw(_("School must belong to the selected Organization."), title=_("Invalid School Scope"))


def _validate_employee_scope(
    employee: str | None, organization: str | None, school: str | None
) -> dict[str, Any] | None:
    if not employee:
        return None

    row = frappe.db.get_value(
        "Employee",
        employee,
        [
            "name",
            "employee_full_name",
            "organization",
            "school",
            "department",
            "expense_approver",
            "employment_status",
        ],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Employee is invalid."))
    if row.organization and organization and row.organization != organization:
        frappe.throw(_("Employee must belong to the selected Organization."))
    if school and row.school and row.school != school:
        frappe.throw(_("Employee must belong to the selected School."))
    return dict(row)


def _validate_account(
    account_name: str | None,
    organization: str | None,
    *,
    label: str,
    root_types: set[str] | None = None,
    account_types: set[str] | None = None,
) -> dict[str, Any] | None:
    account_name = _clean_text(account_name)
    if not account_name:
        return None

    account = frappe.db.get_value(
        "Account",
        account_name,
        ["name", "organization", "is_group", "root_type", "account_type"],
        as_dict=True,
    )
    if not account:
        frappe.throw(_("{label} was not found.").format(label=label))
    if organization and account.organization != organization:
        frappe.throw(_("{label} must belong to the selected Organization.").format(label=label))
    if cint(account.is_group or 0) == 1:
        frappe.throw(_("{label} cannot be a group account.").format(label=label))
    if root_types and account.root_type not in root_types:
        frappe.throw(
            _("{label} must be in one of these root types: {root_types}.").format(
                label=label,
                root_types=", ".join(sorted(root_types)),
            )
        )
    if account_types and account.account_type not in account_types:
        frappe.throw(
            _("{label} must be one of these account types: {account_types}.").format(
                label=label,
                account_types=", ".join(sorted(account_types)),
            )
        )
    return dict(account)


def _lock_expense_claim_for_update(expense_claim: str) -> dict[str, Any]:
    rows = frappe.db.sql(
        """
        SELECT
            name,
            status,
            sanctioned_total,
            paid_amount,
            outstanding_amount
        FROM `tabExpense Claim`
        WHERE name = %s
        FOR UPDATE
        """,
        (expense_claim,),
        as_dict=True,
    )
    if not rows:
        frappe.throw(_("Expense Claim {claim} was not found.").format(claim=expense_claim))
    return dict(rows[0])


def _enforce_edit_lock(doc) -> None:
    previous = doc.get_doc_before_save()
    if not previous or doc.flags.ignore_expense_claim_lock:
        return

    if previous.status in EXPENSE_CLAIM_LOCKED_STATUSES:
        frappe.throw(_("Expense Claim is locked after submission. Use the workflow actions instead."))


def validate_expense_claim(doc) -> None:
    _enforce_edit_lock(doc)

    status = _clean_text(doc.status) or "Draft"
    if status not in EXPENSE_CLAIM_STATUSES:
        frappe.throw(_("Invalid Expense Claim status."))
    doc.status = status

    employee_row = _validate_employee_scope(doc.employee, doc.organization, doc.school)
    if employee_row:
        doc.organization = doc.organization or employee_row.get("organization")
        doc.school = doc.school or employee_row.get("school")
        doc.department = employee_row.get("department")
        doc.employee_name = employee_row.get("employee_full_name")
        if (doc.is_new() or doc.status == "Draft" or not doc.expense_approver) and employee_row.get("expense_approver"):
            doc.expense_approver = employee_row.get("expense_approver")

    _validate_school_organization(doc.school, doc.organization)

    if doc.organization and not doc.currency:
        doc.currency = frappe.db.get_value("Organization", doc.organization, "default_currency")

    if not doc.claim_date:
        doc.claim_date = getdate()

    if doc.status in {"Submitted", "Needs Info", "Approved"} and not doc.expense_approver:
        frappe.throw(
            _(
                "No Expense Approver is set for this employee. Ask HR to set Employee Expense Approver before submitting."
            )
        )

    claimed_total = 0.0
    sanctioned_total = 0.0
    for row in doc.get("items") or []:
        category = _clean_text(getattr(row, "expense_category", None))
        if category not in EXPENSE_CLAIM_CATEGORIES:
            frappe.throw(_("Invalid expense category: {category}").format(category=category or _("blank")))
        if not _clean_text(getattr(row, "description", None)):
            frappe.throw(_("Each Expense Claim row requires a description."))
        if not getattr(row, "expense_date", None):
            frappe.throw(_("Each Expense Claim row requires an expense date."))

        claimed_amount = money(getattr(row, "claimed_amount", 0) or 0)
        if claimed_amount <= 0:
            frappe.throw(_("Claimed amount must be greater than zero."))

        if getattr(row, "sanctioned_amount", None) in (None, "") or status in {
            "Draft",
            "Submitted",
            "Needs Info",
        }:
            row.sanctioned_amount = claimed_amount
        sanctioned_amount = money(getattr(row, "sanctioned_amount", 0) or 0)
        if sanctioned_amount < 0:
            frappe.throw(_("Sanctioned amount cannot be negative."))
        if sanctioned_amount > claimed_amount and status in {
            "Submitted",
            "Needs Info",
            "Approved",
            "Payable Posted",
            "Paid",
        }:
            frappe.throw(_("Sanctioned amount cannot exceed claimed amount."))

        _validate_account(
            getattr(row, "expense_account", None),
            doc.organization,
            label=_("Expense Account"),
            root_types={"Expense"},
        )

        claimed_total = money(claimed_total + claimed_amount)
        sanctioned_total = money(sanctioned_total + sanctioned_amount)

    if doc.status not in {"Draft", "Cancelled"} and not (doc.get("items") or []):
        frappe.throw(_("Expense Claim requires at least one expense item before submission."))

    doc.claimed_total = claimed_total
    doc.sanctioned_total = sanctioned_total
    doc.paid_amount = clamp_money(money(doc.paid_amount or 0))
    if doc.paid_amount < 0:
        frappe.throw(_("Paid amount cannot be negative."))

    if doc.payable_account:
        _validate_account(
            doc.payable_account,
            doc.organization,
            label=_("Payable Account"),
            root_types={"Liability"},
            account_types={"Payable"},
        )

    if doc.status in {"Payable Posted", "Paid"}:
        if not doc.payable_account:
            frappe.throw(_("A payable account is required once the Expense Claim is posted to payable."))
        if is_zero(doc.sanctioned_total):
            frappe.throw(_("Cannot post a zero-value Expense Claim to payable."))
        doc.outstanding_amount = clamp_money(doc.sanctioned_total - doc.paid_amount)
    else:
        doc.outstanding_amount = 0

    if doc.status == "Paid" and not is_zero(doc.outstanding_amount):
        frappe.throw(_("Paid Expense Claims cannot have an outstanding amount."))


def _ensure_claim_write_access(doc, user: str | None = None) -> None:
    user = user or frappe.session.user
    if not frappe.has_permission("Expense Claim", doc=doc, ptype="write", user=user):
        frappe.throw(_("You do not have permission to modify this Expense Claim."), frappe.PermissionError)


def _ensure_decision_access(doc, user: str | None = None) -> None:
    user = user or frappe.session.user
    roles = _get_roles(user)
    if user == doc.expense_approver or roles & EXPENSE_APPROVAL_OVERRIDE_ROLES:
        return
    frappe.throw(_("Only the assigned Expense Approver or HR can decide this Expense Claim."), frappe.PermissionError)


def _ensure_finance_access(user: str | None = None) -> None:
    user = user or frappe.session.user
    if _get_roles(user) & EXPENSE_FINANCE_ROLES:
        return
    frappe.throw(_("Only finance-authorized roles can process Expense Claim accounting."), frappe.PermissionError)


def _native_assign_add(payload: dict[str, Any]) -> None:
    from frappe.desk.form.assign_to import add as assign_add

    assign_add(payload)


def _claimant_user(doc) -> str | None:
    if not doc.employee:
        return None
    return _clean_text(frappe.db.get_value("Employee", doc.employee, "user_id"))


def _todo_description(kind: str, message: str) -> str:
    return f"{EXPENSE_CLAIM_TODO_MARKER}:{kind} {message}"


def _todo_kind_matches(description: str | None, kinds: set[str] | None) -> bool:
    if not kinds:
        return True
    description = description or ""
    return any(f"{EXPENSE_CLAIM_TODO_MARKER}:{kind}" in description for kind in kinds)


def _close_expense_claim_todos(
    expense_claim: str,
    *,
    kinds: set[str] | None = None,
    allocated_to: str | None = None,
) -> None:
    if not expense_claim:
        return

    filters: dict[str, Any] = {
        "reference_type": "Expense Claim",
        "reference_name": expense_claim,
        "status": "Open",
    }
    if allocated_to:
        filters["allocated_to"] = allocated_to

    rows = frappe.get_all(
        "ToDo",
        filters=filters,
        fields=["name", "description"],
        limit=500,
        ignore_permissions=True,
    )
    for row in rows:
        if _todo_kind_matches(row.get("description"), kinds):
            frappe.db.set_value("ToDo", row.get("name"), "status", "Closed", update_modified=False)


def _assign_expense_claim_todo(
    doc,
    *,
    allocated_to: str | None,
    kind: str,
    message: str,
    due_in_days: int | None = None,
) -> None:
    allocated_to = _clean_text(allocated_to)
    if not allocated_to:
        return

    _close_expense_claim_todos(doc.name, kinds={kind}, allocated_to=allocated_to)
    payload: dict[str, Any] = {
        "doctype": "Expense Claim",
        "name": doc.name,
        "assign_to": [allocated_to],
        "description": _todo_description(kind, message),
        "notify": 1,
    }
    if due_in_days is not None:
        payload["due_date"] = add_days(getdate(), due_in_days)
    _native_assign_add(payload)


def _assign_approver_review_todo(doc) -> None:
    message = _("Review expense claim {claim}: {title}").format(
        claim=doc.name,
        title=doc.claim_title or doc.name,
    )
    _assign_expense_claim_todo(
        doc,
        allocated_to=doc.expense_approver,
        kind=EXPENSE_CLAIM_TODO_APPROVER_REVIEW,
        message=message,
        due_in_days=2,
    )


def _assign_claimant_update_todo(doc) -> None:
    claimant_user = _claimant_user(doc)
    message = _("Update expense claim {claim}: {title}").format(
        claim=doc.name,
        title=doc.claim_title or doc.name,
    )
    _assign_expense_claim_todo(
        doc,
        allocated_to=claimant_user,
        kind=EXPENSE_CLAIM_TODO_CLAIMANT_UPDATE,
        message=message,
        due_in_days=3,
    )


def _finance_user_can_receive_claim_todo(doc, user: str) -> bool:
    roles = _get_roles(user)
    if not (roles & EXPENSE_FINANCE_TODO_ROLES):
        return False
    if _is_administrator(user) or "System Manager" in roles:
        return True

    orgs = set(_get_org_scope(user))
    if not orgs or doc.organization not in orgs:
        return False

    schools = set(_get_school_scope(user))
    doc_school = (doc.school or "").strip()
    if schools and doc_school and doc_school not in schools:
        return False
    return True


def _finance_todo_users(doc) -> list[str]:
    role_rows = frappe.get_all(
        "Has Role",
        filters={"role": ["in", sorted(EXPENSE_FINANCE_TODO_ROLES)]},
        fields=["parent"],
        limit=1000,
        ignore_permissions=True,
    )
    candidates = sorted({(row.get("parent") or "").strip() for row in role_rows if (row.get("parent") or "").strip()})
    if not candidates:
        return []

    user_rows = frappe.get_all(
        "User",
        filters={"name": ["in", candidates], "enabled": 1},
        fields=["name"],
        limit=1000,
        ignore_permissions=True,
    )
    return [
        row.get("name")
        for row in user_rows
        if row.get("name") and _finance_user_can_receive_claim_todo(doc, row.get("name"))
    ]


def _assign_finance_todos(doc, *, kind: str) -> None:
    if kind == EXPENSE_CLAIM_TODO_FINANCE_PAY:
        message = _("Pay expense claim {claim}: {title}").format(
            claim=doc.name,
            title=doc.claim_title or doc.name,
        )
        due_in_days = 2
    else:
        message = _("Post payable for expense claim {claim}: {title}").format(
            claim=doc.name,
            title=doc.claim_title or doc.name,
        )
        due_in_days = 2

    for user in _finance_todo_users(doc):
        _assign_expense_claim_todo(
            doc,
            allocated_to=user,
            kind=kind,
            message=message,
            due_in_days=due_in_days,
        )


def _replace_claim_items(doc, rows: list[dict[str, Any]]) -> None:
    doc.set("items", [])
    for row in rows:
        doc.append(
            "items",
            {
                "expense_date": row.get("expense_date"),
                "expense_category": row.get("expense_category"),
                "description": row.get("description"),
                "claimed_amount": flt(row.get("claimed_amount") or 0),
                "sanctioned_amount": flt(row.get("sanctioned_amount") or row.get("claimed_amount") or 0),
                "expense_account": row.get("expense_account"),
            },
        )


def _populate_claim_from_payload(doc, payload: dict[str, Any], *, acting_user: str | None = None) -> None:
    employee = get_current_employee(acting_user)
    doc.employee = employee.get("name")
    doc.organization = employee.get("organization")
    doc.school = employee.get("school")
    doc.department = employee.get("department")
    doc.employee_name = employee.get("employee_full_name")
    doc.expense_approver = employee.get("expense_approver")
    doc.claim_title = payload.get("claim_title")
    doc.claim_date = payload.get("claim_date") or getdate()
    doc.purpose = payload.get("purpose")
    _replace_claim_items(doc, list(payload.get("items") or []))


def save_draft_claim(payload: dict[str, Any], *, acting_user: str | None = None):
    acting_user = acting_user or frappe.session.user
    claim_name = _clean_text(payload.get("expense_claim"))

    if claim_name:
        doc = frappe.get_doc("Expense Claim", claim_name)
        _ensure_claim_write_access(doc, acting_user)
        if doc.status not in {"Draft", "Needs Info"}:
            frappe.throw(_("Only draft or needs-info Expense Claims can be edited before submission."))
    else:
        doc = frappe.new_doc("Expense Claim")
        doc.status = "Draft"

    _populate_claim_from_payload(doc, payload, acting_user=acting_user)
    doc.flags.ignore_expense_claim_lock = True
    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)
    return frappe.get_doc("Expense Claim", doc.name)


def submit_claim(expense_claim: str, *, acting_user: str | None = None):
    acting_user = acting_user or frappe.session.user
    doc = frappe.get_doc("Expense Claim", expense_claim)
    _ensure_claim_write_access(doc, acting_user)

    current_employee = get_current_employee(acting_user)
    if doc.employee != current_employee.get("name") and "System Manager" not in _get_roles(acting_user):
        frappe.throw(_("Only the claimant can submit this Expense Claim."), frappe.PermissionError)
    if doc.status not in {"Draft", "Needs Info"}:
        frappe.throw(_("Only draft or needs-info Expense Claims can be submitted."))
    if not doc.expense_approver:
        frappe.throw(
            _(
                "No Expense Approver is set for this employee. Ask HR to set Employee Expense Approver before submitting."
            )
        )

    doc.flags.ignore_expense_claim_lock = True
    doc.status = "Submitted"
    doc.submitted_by = acting_user
    doc.submitted_on = now_datetime()
    doc.save(ignore_permissions=True)
    _close_expense_claim_todos(doc.name, kinds={EXPENSE_CLAIM_TODO_CLAIMANT_UPDATE})
    _assign_approver_review_todo(doc)
    return frappe.get_doc("Expense Claim", doc.name)


def decide_claim(
    expense_claim: str,
    *,
    decision: str,
    notes: str | None = None,
    sanctioned_items: list[dict[str, Any]] | None = None,
    acting_user: str | None = None,
):
    acting_user = acting_user or frappe.session.user
    doc = frappe.get_doc("Expense Claim", expense_claim)
    _ensure_decision_access(doc, acting_user)

    if doc.status not in {"Submitted"}:
        frappe.throw(_("Only submitted Expense Claims can be approved, rejected, or sent back for information."))

    decision = (_clean_text(decision) or "").lower().replace("-", "_")
    if decision == "needs_info":
        decision = "request_info"
    if decision not in {"approve", "reject", "request_info"}:
        frappe.throw(_("Decision must be approve, reject, or request_info."))

    doc.flags.ignore_expense_claim_lock = True
    if decision == "request_info":
        if not _clean_text(notes):
            frappe.throw(_("Explain what information or receipts are needed before sending the claim back."))
        doc.status = "Needs Info"
    elif decision == "reject":
        doc.status = "Rejected"
    else:
        sanctioned_by_row = {
            _clean_text(row.get("row_name")): row for row in sanctioned_items or [] if _clean_text(row.get("row_name"))
        }
        for row in doc.get("items") or []:
            adjustment = sanctioned_by_row.get(_clean_text(getattr(row, "name", None)))
            if adjustment:
                row.sanctioned_amount = flt(adjustment.get("sanctioned_amount") or 0)
            elif getattr(row, "sanctioned_amount", None) in (None, ""):
                row.sanctioned_amount = flt(getattr(row, "claimed_amount", 0) or 0)
        doc.status = "Approved"

    doc.decision_by = acting_user
    doc.decision_on = now_datetime()
    doc.decision_notes = notes or ""
    doc.save(ignore_permissions=True)
    _close_expense_claim_todos(
        doc.name,
        kinds={EXPENSE_CLAIM_TODO_APPROVER_REVIEW, EXPENSE_CLAIM_TODO_CLAIMANT_UPDATE},
    )
    if decision == "request_info":
        _assign_claimant_update_todo(doc)
    elif decision == "approve":
        _assign_finance_todos(doc, kind=EXPENSE_CLAIM_TODO_FINANCE_POST)
    else:
        _close_expense_claim_todos(doc.name)
    return frappe.get_doc("Expense Claim", doc.name)


def request_claim_info(expense_claim: str, *, notes: str, acting_user: str | None = None):
    acting_user = acting_user or frappe.session.user
    _ensure_finance_access(acting_user)

    doc = frappe.get_doc("Expense Claim", expense_claim)
    if doc.status != "Approved":
        frappe.throw(_("Only approved Expense Claims can be sent back by finance before payable posting."))
    if not _clean_text(notes):
        frappe.throw(_("Explain what information or receipts are needed before sending the claim back."))

    doc.flags.ignore_expense_claim_lock = True
    doc.status = "Needs Info"
    doc.decision_by = acting_user
    doc.decision_on = now_datetime()
    doc.decision_notes = notes
    doc.save(ignore_permissions=True)
    _close_expense_claim_todos(
        doc.name,
        kinds={EXPENSE_CLAIM_TODO_FINANCE_POST, EXPENSE_CLAIM_TODO_FINANCE_PAY},
    )
    _assign_claimant_update_todo(doc)
    return frappe.get_doc("Expense Claim", doc.name)


def _apply_finance_account_mapping(
    doc, *, expense_account: str | None, item_accounts: list[dict[str, Any]] | None
) -> None:
    account_by_row = {
        _clean_text(row.get("row_name")): _clean_text(row.get("expense_account"))
        for row in item_accounts or []
        if _clean_text(row.get("row_name")) and _clean_text(row.get("expense_account"))
    }
    default_expense_account = _clean_text(expense_account)
    if not default_expense_account and not account_by_row:
        frappe.throw(_("Select an Expense Account before posting this Expense Claim."))

    for row in doc.get("items") or []:
        row_expense_account = account_by_row.get(_clean_text(getattr(row, "name", None))) or default_expense_account
        if not row_expense_account:
            frappe.throw(_("Every Expense Claim row must have an Expense Account before payable posting."))
        _validate_account(
            row_expense_account,
            doc.organization,
            label=_("Expense Account"),
            root_types={"Expense"},
        )
        row.expense_account = row_expense_account


def post_claim_payable(
    expense_claim: str,
    *,
    payable_account: str,
    expense_account: str | None = None,
    item_accounts: list[dict[str, Any]] | None = None,
    posting_date=None,
    remarks: str | None = None,
    acting_user: str | None = None,
):
    acting_user = acting_user or frappe.session.user
    _ensure_finance_access(acting_user)
    _lock_expense_claim_for_update(expense_claim)
    doc = frappe.get_doc("Expense Claim", expense_claim)

    if doc.status == "Payable Posted":
        _assign_finance_todos(doc, kind=EXPENSE_CLAIM_TODO_FINANCE_PAY)
        return doc
    if doc.status != "Approved":
        frappe.throw(_("Only approved Expense Claims can be posted to payable."))
    if is_zero(doc.sanctioned_total):
        frappe.throw(_("Cannot post a zero-value Expense Claim to payable."))

    _validate_account(
        payable_account,
        doc.organization,
        label=_("Payable Account"),
        root_types={"Liability"},
        account_types={"Payable"},
    )
    _apply_finance_account_mapping(doc, expense_account=expense_account, item_accounts=item_accounts)

    posting_date = posting_date or getdate()
    validate_posting_date(doc.organization, posting_date)
    payable_entries = []
    for row in doc.get("items") or []:
        sanctioned_amount = money(getattr(row, "sanctioned_amount", 0) or 0)
        if is_zero(sanctioned_amount):
            continue
        payable_entries.append(
            {
                "organization": doc.organization,
                "posting_date": posting_date,
                "account": row.expense_account,
                "party_type": None,
                "party": None,
                "against": payable_account,
                "remarks": remarks or doc.remarks or doc.claim_title,
                "debit": sanctioned_amount,
                "credit": 0,
                "school": doc.school,
            }
        )

    payable_entries.append(
        {
            "organization": doc.organization,
            "posting_date": posting_date,
            "account": payable_account,
            "party_type": "Employee",
            "party": doc.employee,
            "against": ", ".join(
                sorted({row.expense_account for row in doc.get("items") or [] if row.expense_account})
            ),
            "remarks": remarks or doc.remarks or doc.claim_title,
            "debit": 0,
            "credit": doc.sanctioned_total,
            "school": doc.school,
        }
    )
    make_gl_entries(payable_entries, "Expense Claim", doc.name)

    doc.flags.ignore_expense_claim_lock = True
    doc.status = "Payable Posted"
    doc.payable_account = payable_account
    doc.payable_posted_by = acting_user
    doc.payable_posted_on = now_datetime()
    doc.paid_amount = 0
    doc.outstanding_amount = doc.sanctioned_total
    doc.remarks = remarks or doc.remarks
    doc.save(ignore_permissions=True)
    _close_expense_claim_todos(doc.name, kinds={EXPENSE_CLAIM_TODO_FINANCE_POST})
    _assign_finance_todos(doc, kind=EXPENSE_CLAIM_TODO_FINANCE_PAY)
    return frappe.get_doc("Expense Claim", doc.name)


def create_claim_payment(
    expense_claim: str,
    *,
    paid_to: str,
    paid_amount: float | None = None,
    posting_date=None,
    remarks: str | None = None,
    acting_user: str | None = None,
):
    acting_user = acting_user or frappe.session.user
    _ensure_finance_access(acting_user)
    doc = frappe.get_doc("Expense Claim", expense_claim)

    if doc.status not in {"Payable Posted"}:
        frappe.throw(_("Only payable-posted Expense Claims can be paid."))
    if is_zero(doc.outstanding_amount):
        frappe.throw(_("This Expense Claim has no outstanding amount."))

    _validate_account(
        paid_to,
        doc.organization,
        label=_("Bank or Cash Account"),
        root_types={"Asset"},
        account_types={"Bank", "Cash"},
    )
    amount = money(paid_amount if paid_amount is not None else doc.outstanding_amount)
    if amount <= 0:
        frappe.throw(_("Paid Amount must be greater than zero."))
    if amount > money(doc.outstanding_amount) and not is_zero(amount - money(doc.outstanding_amount)):
        frappe.throw(_("Paid Amount cannot exceed outstanding amount."))

    payment = frappe.new_doc("Payment Entry")
    payment.payment_type = "Pay"
    payment.party_type = "Employee"
    payment.party = doc.employee
    payment.organization = doc.organization
    payment.school = doc.school
    payment.posting_date = posting_date or getdate()
    payment.paid_to = paid_to
    payment.paid_amount = amount
    payment.remarks = remarks or _("Expense Claim payment for {claim}").format(claim=doc.name)
    payment.append(
        "references",
        {
            "reference_doctype": "Expense Claim",
            "reference_name": doc.name,
            "total_amount": doc.sanctioned_total,
            "outstanding_amount": doc.outstanding_amount,
            "allocated_amount": amount,
        },
    )
    payment.insert(ignore_permissions=True)
    payment.submit()
    return frappe.get_doc("Payment Entry", payment.name)


def cancel_claim(expense_claim: str, *, notes: str | None = None, acting_user: str | None = None):
    acting_user = acting_user or frappe.session.user
    doc = frappe.get_doc("Expense Claim", expense_claim)

    if doc.status == "Cancelled":
        return doc
    if doc.status == "Paid":
        frappe.throw(_("Paid Expense Claims cannot be cancelled. Cancel the Payment Entry first."))
    if doc.status == "Payable Posted" and not is_zero(doc.paid_amount):
        frappe.throw(_("Partially paid Expense Claims cannot be cancelled. Cancel the Payment Entry first."))
    if doc.status == "Payable Posted":
        _ensure_finance_access(acting_user)
        cancel_gl_entries("Expense Claim", doc.name)
    else:
        _ensure_claim_write_access(doc, acting_user)

    doc.flags.ignore_expense_claim_lock = True
    doc.status = "Cancelled"
    doc.decision_notes = notes or doc.decision_notes
    doc.outstanding_amount = 0
    doc.save(ignore_permissions=True)
    _close_expense_claim_todos(doc.name)
    return frappe.get_doc("Expense Claim", doc.name)


def apply_expense_claim_payment(
    expense_claim: str,
    *,
    allocated_amount: float,
    payment_entry: str,
    posting_datetime=None,
    cancel: bool = False,
) -> None:
    row = _lock_expense_claim_for_update(expense_claim)

    delta = money(allocated_amount or 0)
    current_paid = money(row.paid_amount or 0)
    paid_amount = clamp_money(current_paid - delta if cancel else current_paid + delta)
    sanctioned_total = money(row.sanctioned_total or 0)
    if paid_amount < 0:
        frappe.throw(_("Expense Claim paid amount cannot become negative."))
    if paid_amount > sanctioned_total and not is_zero(paid_amount - sanctioned_total):
        frappe.throw(_("Expense Claim paid amount cannot exceed sanctioned total."))

    outstanding = clamp_money(sanctioned_total - paid_amount)
    status = "Paid" if is_zero(outstanding) and paid_amount > 0 else "Payable Posted"
    values = {
        "paid_amount": paid_amount,
        "outstanding_amount": outstanding,
        "status": status,
        "payment_entry": None if cancel else payment_entry,
    }
    if status == "Paid":
        values["paid_on"] = posting_datetime or now_datetime()
    elif cancel:
        values["paid_on"] = None
    frappe.db.set_value("Expense Claim", expense_claim, values, update_modified=False)
    if status == "Paid":
        _close_expense_claim_todos(expense_claim, kinds={EXPENSE_CLAIM_TODO_FINANCE_PAY})
    else:
        _assign_finance_todos(frappe.get_doc("Expense Claim", expense_claim), kind=EXPENSE_CLAIM_TODO_FINANCE_PAY)


def _serialize_items(rows: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "row_name": row.get("name"),
            "expense_date": row.get("expense_date"),
            "expense_category": row.get("expense_category"),
            "description": row.get("description"),
            "claimed_amount": flt(row.get("claimed_amount") or 0),
            "sanctioned_amount": flt(row.get("sanctioned_amount") or 0),
            "expense_account": row.get("expense_account"),
        }
        for row in sorted(rows, key=lambda item: cint(item.get("idx") or 0))
    ]


def _serialize_receipts(expense_claim: str, rows: list[Any]) -> list[dict[str, Any]]:
    from ifitwala_ed.api.expense_claim_receipts import serialize_expense_claim_receipt_row

    return [
        serialize_expense_claim_receipt_row(expense_claim, frappe._dict(row))
        for row in sorted(rows, key=lambda item: cint(item.get("idx") or 0))
    ]


def serialize_claim(
    row: dict[str, Any], *, items: list[Any] | None = None, receipts: list[Any] | None = None
) -> dict[str, Any]:
    claim = {field: row.get(field) for field in EXPENSE_CLAIM_FIELDS}
    claim["claimed_total"] = flt(claim.get("claimed_total") or 0)
    claim["sanctioned_total"] = flt(claim.get("sanctioned_total") or 0)
    claim["paid_amount"] = flt(claim.get("paid_amount") or 0)
    claim["outstanding_amount"] = flt(claim.get("outstanding_amount") or 0)
    claim["items"] = _serialize_items(items or [])
    claim["receipts"] = _serialize_receipts(row.get("name"), receipts or [])
    return claim


def _fetch_claim_children(claim_names: list[str]) -> tuple[dict[str, list[Any]], dict[str, list[Any]]]:
    if not claim_names:
        return {}, {}

    item_rows = frappe.get_all(
        "Expense Claim Item",
        filters={"parent": ["in", claim_names], "parenttype": "Expense Claim"},
        fields=[
            "name",
            "parent",
            "idx",
            "expense_date",
            "expense_category",
            "description",
            "claimed_amount",
            "sanctioned_amount",
            "expense_account",
        ],
        order_by="parent asc, idx asc",
        limit=max(100, len(claim_names) * 20),
    )
    receipt_rows = frappe.get_all(
        "Attached Document",
        filters={"parent": ["in", claim_names], "parenttype": "Expense Claim", "parentfield": "receipts"},
        fields=[
            "name",
            "parent",
            "idx",
            "section_break_sbex",
            "file",
            "external_url",
            "description",
            "file_name",
            "file_size",
        ],
        order_by="parent asc, idx asc",
        limit=max(100, len(claim_names) * 20),
    )
    items_by_parent: dict[str, list[Any]] = defaultdict(list)
    receipts_by_parent: dict[str, list[Any]] = defaultdict(list)
    for row in item_rows:
        items_by_parent[row.get("parent")].append(row)
    for row in receipt_rows:
        receipts_by_parent[row.get("parent")].append(row)
    return items_by_parent, receipts_by_parent


def _serialize_claim_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claim_names = [row.get("name") for row in rows if row.get("name")]
    items_by_parent, receipts_by_parent = _fetch_claim_children(claim_names)
    return [
        serialize_claim(
            row,
            items=items_by_parent.get(row.get("name"), []),
            receipts=receipts_by_parent.get(row.get("name"), []),
        )
        for row in rows
    ]


def _scope_filters_for_finance(user: str | None = None) -> dict[str, Any]:
    user = user or frappe.session.user
    if _is_administrator(user) or "System Manager" in _get_roles(user):
        return {}

    filters: dict[str, Any] = {}
    orgs = _get_org_scope(user)
    if not orgs:
        return {"name": "__no_access__"}
    filters["organization"] = ["in", orgs]
    schools = _get_school_scope(user)
    if schools:
        filters["school"] = ["in", schools + [""]]
    return filters


def _fetch_my_claims(employee: str) -> list[dict[str, Any]]:
    rows = frappe.get_all(
        "Expense Claim",
        filters={"employee": employee},
        fields=EXPENSE_CLAIM_FIELDS,
        order_by="modified desc",
        limit=50,
    )
    return _serialize_claim_rows(rows)


def _fetch_approval_queue(user: str) -> list[dict[str, Any]]:
    rows = frappe.get_all(
        "Expense Claim",
        filters={"expense_approver": user, "status": "Submitted"},
        fields=EXPENSE_CLAIM_FIELDS,
        order_by="submitted_on asc",
        limit=50,
    )
    return _serialize_claim_rows(rows)


def _fetch_finance_queue(user: str) -> list[dict[str, Any]]:
    roles = _get_roles(user)
    if not (roles & EXPENSE_FINANCE_ROLES):
        return []

    filters = {
        "status": ["in", ["Approved", "Payable Posted"]],
        **_scope_filters_for_finance(user),
    }
    if filters.get("name") == "__no_access__":
        return []
    rows = frappe.get_all(
        "Expense Claim",
        filters=filters,
        fields=EXPENSE_CLAIM_FIELDS,
        order_by="modified asc",
        limit=50,
    )
    return _serialize_claim_rows(rows)


def _account_options(
    user: str, *, root_type: str | None = None, account_types: set[str] | None = None
) -> list[dict[str, str]]:
    roles = _get_roles(user)
    if not (roles & EXPENSE_FINANCE_ROLES):
        return []

    filters: dict[str, Any] = {"is_group": 0, "disabled": 0}
    if root_type:
        filters["root_type"] = root_type
    if account_types:
        filters["account_type"] = ["in", sorted(account_types)]

    if not (_is_administrator(user) or "System Manager" in roles):
        orgs = _get_org_scope(user)
        if not orgs:
            return []
        filters["organization"] = ["in", orgs]

    rows = frappe.get_all(
        "Account",
        filters=filters,
        fields=["name", "account_name", "account_number", "organization", "root_type", "account_type"],
        order_by="account_number asc, account_name asc",
        limit=200,
    )
    return [
        {
            "value": row.get("name"),
            "label": row.get("account_name") or row.get("name"),
            "account_number": row.get("account_number"),
            "organization": row.get("organization"),
            "root_type": row.get("root_type"),
            "account_type": row.get("account_type"),
        }
        for row in rows
    ]


def build_expense_claim_board(user: str | None = None) -> dict[str, Any]:
    user = user or frappe.session.user
    employee = get_current_employee(user)
    roles = _get_roles(user)
    my_claims = _fetch_my_claims(employee.get("name"))
    approval_queue = _fetch_approval_queue(user)
    finance_queue = _fetch_finance_queue(user)

    return {
        "viewer": {
            "user": user,
            "employee": employee.get("name"),
            "employee_name": employee.get("employee_full_name"),
            "organization": employee.get("organization"),
            "school": employee.get("school"),
            "department": employee.get("department"),
            "expense_approver": employee.get("expense_approver"),
            "can_decide": bool(approval_queue or roles & EXPENSE_APPROVAL_OVERRIDE_ROLES),
            "can_finance": bool(roles & EXPENSE_FINANCE_ROLES),
        },
        "defaults": {
            "claim_date": getdate(),
        },
        "options": {
            "categories": list(EXPENSE_CLAIM_CATEGORIES),
            "expense_accounts": _account_options(user, root_type="Expense"),
            "payable_accounts": _account_options(user, root_type="Liability", account_types={"Payable"}),
            "bank_accounts": _account_options(user, root_type="Asset", account_types={"Bank", "Cash"}),
        },
        "my_claims": my_claims,
        "approval_queue": approval_queue,
        "finance_queue": finance_queue,
        "stats": {
            "draft": sum(1 for claim in my_claims if claim.get("status") == "Draft"),
            "submitted": sum(1 for claim in my_claims if claim.get("status") == "Submitted"),
            "needs_info": sum(1 for claim in my_claims if claim.get("status") == "Needs Info"),
            "approved": sum(1 for claim in my_claims if claim.get("status") == "Approved"),
            "outstanding": sum(flt(claim.get("outstanding_amount") or 0) for claim in my_claims),
        },
    }
