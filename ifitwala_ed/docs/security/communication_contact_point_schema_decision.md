# Communication Contact Point Schema Decision

Status: Approved schema decision; DocType and service helpers implemented
Last updated: 2026-05-22
Code refs:
- `ifitwala_ed/governance/doctype/communication_contact_point/communication_contact_point.json`
- `ifitwala_ed/governance/doctype/communication_contact_point/communication_contact_point.py`
- `ifitwala_ed/contacts/contact_privacy.py`
Test refs:
- `ifitwala_ed/governance/doctype/communication_contact_point/test_communication_contact_point.py`
- `ifitwala_ed/contacts/test_contact_privacy.py`

This document approves the schema and runtime contract for `Communication Contact Point`.

The DocType and first service helpers are implemented. Legacy native `Contact` reads/writes are not retired yet, and no migration patch has been added.

## 1. Decision

`Communication Contact Point` will be a single internal DocType in the existing `Governance` module.

Reasons:

1. `Governance` already owns privacy/audit approval objects.
2. Ifitwala Ed must not claim a `Contacts` module because Frappe core owns native `Contact`, `Address`, `Contact Email`, `Contact Phone`, `Salutation`, `Gender`, and related DocTypes there.
3. A single row-per-channel-purpose table is enough for Guardian-first migration and avoids over-modeling before runtime behavior is proven.

Rejected alternatives:

- Native Frappe `Contact` as canonical people/contact registry.
- A Desk-visible address book.
- Split `Contact Point` plus `Contact Point Purpose` DocTypes in the first implementation.
- A module named `Contacts` inside Ifitwala Ed.

## 2. Package Shape

The implementation must use the full Frappe DocType package shape:

```text
ifitwala_ed/governance/doctype/communication_contact_point/
- __init__.py
- communication_contact_point.json
- communication_contact_point.py
```

The controller must include the matching class:

```python
from frappe.model.document import Document


class CommunicationContactPoint(Document):
    ...
```

Child-table shortcuts are not allowed. This DocType is not a child table.

## 3. Approved Fields

Approved DocType name:

```text
Communication Contact Point
```

Approved autoname:

```text
CCP-.YY.-.MM.-.#####
```

Approved field set:

| Fieldname | Type | Required | Notes |
| --- | --- | ---: | --- |
| `owner_doctype` | Link -> DocType | Yes | Domain record that owns update/erasure responsibility. |
| `owner_name` | Dynamic Link | Yes | Options: `owner_doctype`. |
| `subject_doctype` | Link -> DocType | Yes | Person/entity being contacted. Usually same as owner for Guardian, Student, Employee, Applicant, and Inquiry rows. |
| `subject_name` | Dynamic Link | Yes | Options: `subject_doctype`. |
| `organization` | Link -> Organization | Yes | Tenant anchor. Parent organizations include descendants for scoped resolution. |
| `school` | Link -> School | No | Required by service validation for school-owned education records. |
| `channel_type` | Select | Yes | Allowed values: `email`, `phone`, `address`. |
| `purpose` | Data | Yes | Purpose key owned by service constants, not free-form UI text. |
| `value_encrypted` | Long Text | Yes | Service-encrypted raw value. Never list-view, report, or DTO output. |
| `normalized_hash` | Data | Yes | Deterministic keyed HMAC of normalized value and channel. Not a user-facing search key. |
| `masked_display` | Data | Yes | Default UI/API display value. |
| `is_primary` | Check | No | Service enforces at most one active primary per owner/channel/purpose scope. |
| `verified_on` | Datetime | No | Set only by explicit verification workflows. |
| `disabled` | Check | No | Disabled rows are retained for audit/history but excluded from recipient resolution. |

No raw email, phone, mobile, or address field is allowed outside `value_encrypted`.

Initial service-approved owner/subject DocTypes:

```text
Guardian
Student
Student Applicant
Inquiry
Employee
```

Additional owner/subject DocTypes require either this contract to be updated or a domain contract that explicitly references this decision.

## 4. Ownership Semantics

`owner_doctype` and `owner_name` define who owns lifecycle, erasure, and edit authority.

`subject_doctype` and `subject_name` define who or what the endpoint reaches.

Examples:

| Workflow | Owner | Subject |
| --- | --- | --- |
| Guardian phone | `Guardian` | `Guardian` |
| Student email | `Student` | `Student` |
| Employee work phone | `Employee` | `Employee` |
| Applicant-stage email | `Student Applicant` | `Student Applicant` |
| Inquiry lead phone | `Inquiry` | `Inquiry` |

If a future workflow contacts a person related to another business object, the owner remains the business object responsible for the relationship until a first-class subject record exists.

## 5. Purpose Keys

Purpose is mandatory and must be a stable service key.

Initial approved purpose keys:

```text
emergency
billing
admissions_followup
family_consent
school_communication
hr
relationship_crm
export
```

New purpose keys require a contract update or a domain contract that explicitly references this document.

## 6. Service-Only Runtime

`Communication Contact Point` is service-owned.

Rules:

1. No normal Desk list use.
2. No report-builder use.
3. No generic export.
4. No generic whitelisted CRUD endpoint.
5. No client-side filtering of broad contact-point payloads.
6. No `fields=["*"]` retrieval.
7. No direct user insert/update/delete.
8. No `System Manager` product-data bypass.

The DocType permissions should be empty or deny-by-default. Controller methods must enforce service flags for insert/update and must block delete.

Required controller behavior:

```python
def before_insert(self):
    assert service-owned creation

def before_save(self):
    assert service-owned mutation

def before_delete(self):
    frappe.throw(...)
```

## 7. Encryption And Hashing

Raw values are encrypted before storage in `value_encrypted`.

Normalization and hashing rules:

1. Email is lowercased and trimmed.
2. Phone is normalized to a canonical dialable representation before hashing.
3. Address normalization must be conservative; do not collapse meaningful address lines without a domain-specific normalizer.
4. `normalized_hash` must be a keyed HMAC using a site secret, not plain SHA over the raw value.
5. Hash matches are internal service hints only. They must not become a user-facing lookup surface.

Masked display rules:

1. Masked display is computed server-side at write time.
2. Masked display is the default DTO value.
3. Raw values are returned only through explicitly named raw workflows with audit logging.

## 8. Scope And Indexing

Tenant scope is mandatory.

The implementation should add indexes for these read paths:

| Index purpose | Fields |
| --- | --- |
| Owner lookup | `owner_doctype`, `owner_name`, `channel_type`, `disabled` |
| Subject lookup | `subject_doctype`, `subject_name`, `channel_type`, `disabled` |
| Scoped recipient resolution | `organization`, `school`, `purpose`, `channel_type`, `disabled` |
| Deduplication hint | `normalized_hash`, `organization`, `school`, `channel_type`, `disabled` |
| Primary selection | `owner_doctype`, `owner_name`, `purpose`, `channel_type`, `is_primary`, `disabled` |

Selecting a parent organization or school includes descendants only through server-side scope helpers. Sibling isolation remains mandatory.

Exact-match school filtering is allowed only for workflows whose domain contract explicitly rejects descendant inheritance.

## 9. Validation Rules

The controller/service must enforce:

1. `owner_doctype`, `owner_name`, `subject_doctype`, and `subject_name` are present.
2. `organization` is present.
3. `school` is present for Student, Guardian, Student Applicant, and school-owned Inquiry contact points.
4. `channel_type` is one of the approved values.
5. `purpose` is present and approved.
6. `value_encrypted`, `normalized_hash`, and `masked_display` are present for active rows.
7. `normalized_hash` is never computed client-side.
8. Only one active primary row exists per owner/channel/purpose where the service contract says a primary is meaningful.
9. Disabled rows are never recipient-resolution candidates.

## 10. Approved Service Boundary

The first implementation must extend `ifitwala_ed/contacts/contact_privacy.py` rather than adding scattered reads.

Required service functions:

```python
upsert_contact_point(...)
disable_contact_points_for_owner(...)
get_masked_contact_points_for_owner(...)
get_raw_contact_point_value(...)
resolve_contact_point_recipients(...)
```

Existing workflow functions must migrate behind these internals over time:

```python
get_masked_student_contact_summary(...)
get_masked_guardian_contacts_for_student(...)
get_raw_contact_email_options_for_applicant_invite(...)
get_raw_contact_primary_values_for_portal_context(...)
update_family_contact_from_portal_context(...)
assert_contact_not_protected_for_inquiry_reuse(...)
```

Raw reads and raw writes must continue to log through `Contact Access Log`.

Approved export execution must call `assert_approved_contact_export(...)` before resolving raw values.

## 11. Implementation Order

The implementation sequence is locked:

1. Done: Create the `Communication Contact Point` DocType in `Governance`.
2. Done: Add controller/service tests for service-only creation, mutation, no delete, package shape, and no `Contacts` module ownership.
3. Done: Add contact-point write/read helpers without changing existing domain workflows.
4. Partial: Add explicit Guardian contact-point sync helper requiring a verified school context.
5. Not started: Bridge Guardian read paths to contact points with scoped legacy native `Contact` fallback.
6. Not started: Add a one-shot Guardian migration patch.
7. Not started: Retire Guardian native `Contact` write paths after tests and docs prove parity.
8. Not started: Repeat by domain: Student, Student Applicant/Inquiry, Employee, then external relationship CRM surfaces.

No permanent runtime repair or self-heal flow is approved.

Guardian controller note:

- `Guardian` has `organization`, `guardian_email`, and `guardian_mobile_phone`, but no canonical `school` field.
- The service helper `sync_guardian_contact_points(...)` therefore requires an explicit `school` argument.
- Do not call this helper from `Guardian.after_insert` or `Guardian.on_update` until the caller can prove school context from a Student/family relationship.

## 12. Non-Goals

This decision does not implement:

- CSV export generation.
- Bulk migration from native `Contact`.
- New Desk UI.
- Relationship CRM contact-point writes.
- Supplier/external partner contact-point writes.
- Address normalization beyond conservative storage/masking rules.
- Automatic Guardian controller write-through.
- Legacy native `Contact` retirement.

## 13. Acceptance For PR-7

The implemented PR-7 slice satisfies:

1. The DocType lives under `ifitwala_ed/governance/doctype/communication_contact_point/`.
2. The package includes `__init__.py`, `.json`, and `.py` with `CommunicationContactPoint`.
3. The DocType module is `Governance`.
4. Permissions are deny-by-default/service-only.
5. Direct delete is blocked.
6. Direct user insert/update is blocked.
7. No raw values appear in list view, search fields, reports, logs, or DTOs.
8. Tests prove package shape and no `Contacts` module collision.
9. No existing workflow is migrated in the same PR unless explicitly approved.
