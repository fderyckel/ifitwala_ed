# Expense Reimbursement

Status: Canonical Phase 1C runtime contract
Code refs: `ifitwala_ed/hr/doctype/expense_claim/`, `ifitwala_ed/hr/expense_claims.py`, `ifitwala_ed/hr/expense_claim_permissions.py`, `ifitwala_ed/api/expense_claims.py`, `ifitwala_ed/api/expense_claim_receipts.py`, `ifitwala_ed/api/focus_listing.py`, `ifitwala_ed/api/focus_context.py`, `ifitwala_ed/utilities/file_management.py`, `ifitwala_ed/ui-spa/src/pages/staff/ExpenseClaims.vue`, `ifitwala_ed/ui-spa/src/components/focus/ExpenseClaimFocusAction.vue`
Test refs: `ifitwala_ed/hr/test_expense_claim_permissions.py`, `ifitwala_ed/api/test_expense_claim_receipts_unit.py`, `ifitwala_ed/utilities/test_file_management.py`; Frappe site workflow tests pending

## Scope

Expense reimbursement is a staff-first workflow for teachers and employees who paid for school-related expenses and need reimbursement.

Phase 1C deliberately keeps the claimant form category-first:

- staff select one of the default categories
- staff enter date, description, amount, and receipts
- staff do not select Item records
- staff do not select accounts
- accounting maps the approved claim to expense/payable/bank accounts during finance processing

This is separate from supplier invoice purchasing. Supplier, purchase request, purchase invoice, and outbound supplier payment remain a later payables phase.

## Workflow

```mermaid
flowchart LR
    A["Employee drafts claim"] --> B["Employee uploads receipts"]
    B --> C["Employee submits"]
    C --> D["Expense Approver reviews"]
    D -->|Needs Info| H["Employee updates claim"]
    H --> C
    D -->|Approved| E["Accounting reviews receipts and coding"]
    E -->|Needs Info| H
    E --> I["Accounting posts payable"]
    I --> F["Accounting pays employee"]
    D -->|Rejected| G["Claim closed"]
```

The claimant submits. The approver does not submit on behalf of the employee.

The assigned approver is `Employee.expense_approver`. HR and system roles can override approval when required, but the normal school flow is one approver before accounting acts. Accounting is notified after approval, then remains responsible for payable posting and payment.

## Status Contract

`Expense Claim.status` is status-driven, not a submitted DocType lifecycle.

Allowed statuses:

- `Draft`
- `Submitted`
- `Needs Info`
- `Approved`
- `Rejected`
- `Finance Review`
- `Payable Posted`
- `Paid`
- `Cancelled`

`Draft` and `Needs Info` claims are editable by claimants. `Needs Info` is the clarification loop: the approver or finance records `decision_notes`, the employee sees those notes, updates the claim or receipts, then resubmits. Workflow actions update locked claims through named APIs.

## Task And Notification Contract

Expense Claim uses native Frappe `ToDo` as the durable assignment mechanism and the staff Focus List as the user-facing attention surface.

Workflow-owned ToDos:

- on employee submit: assign the approver a review ToDo
- on request info: close approver review ToDos and assign the claimant an update ToDo
- on employee resubmit: close claimant update ToDos and assign the approver a fresh review ToDo
- on approval: close approver review ToDos and assign scoped finance users a finance review ToDo
- on finance request info before payable posting: close finance ToDos and assign the claimant an update ToDo
- on payable posting: close payable-posting ToDos and assign scoped finance users a payment ToDo
- on payment, rejection, or cancellation: close now-obsolete Expense Claim ToDos

Focus List projects these ToDos as Expense Claim focus items. Focus does not decide workflow outcomes; it routes users back to the Expense Claim workspace.

## Accounting Contract

Approval does not post GL.

Accounting reviews approved claims in one simple panel before payable posting:

- receipt count and receipt links
- item/category summary
- one default expense account for the claim
- one payable account
- request-info notes when receipts or details are missing

Accounting posts payable after review by selecting:

- one payable account
- one default expense account, or row-level expense accounts later

Posting creates GL entries against voucher type `Expense Claim`:

- debit expense account rows
- credit payable account with `party_type = Employee`

Payment uses `Payment Entry.payment_type = Pay` with `party_type = Employee` and an `Expense Claim` reference. It debits the employee payable and credits bank/cash.

## Receipt Contract

Receipts use governed Drive upload workflow `expense_claim.receipt`.

The browser receives only server-owned open/preview/thumbnail URLs. It must not construct `/private/...` paths or storage URLs.

Receipt context:

- owner: `Expense Claim`
- primary subject: `Employee`
- data class: `financial`
- purpose: `administrative`
- retention policy: `fixed_7y`
- binding role: `expense_claim_receipt`

Read access is resolved through `Expense Claim` read permission before Drive grants are requested.

Desk receipt uploads must use the `Upload Receipt` action. The Desk form saves a dirty draft before opening the governed uploader so Drive receives a persisted `Expense Claim` name rather than a temporary `new-expense-claim-*` name.

Raw Frappe `File` attachments on `Expense Claim` are non-canonical and are rejected with an actionable message. Receipt files must be persisted through the governed `expense_claim.receipt` upload path.
