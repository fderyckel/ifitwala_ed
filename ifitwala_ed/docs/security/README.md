# Security Documentation Index

Status: Canonical index
Code refs: Listed by canonical doc below
Test refs: Listed by canonical doc below

This folder covers security and privacy architecture that cuts across domain modules.

Read in this order:

1. `contact_data_governance.md`
2. `communication_contact_point_schema_decision.md`

Canonical docs:

- `contact_data_governance.md` - locked target architecture and current gap register for person/contact data governance, native Frappe `Contact`, purpose-bound recipient resolution, exports, raw-value access, and deletion/erasure boundaries.
  Code refs: Listed in the document.
  Test refs: Listed in the document.
- `communication_contact_point_schema_decision.md` - approved schema and runtime contract for the future internal `Communication Contact Point` DocType. This is a design decision only; implementation remains future work.
  Code refs: Planned in the document.
  Test refs: Planned in the document.

Related planned product contracts:

- `../relationship_crm/README.md` - planned education-native Relationship CRM contracts. These do not weaken contact governance or approve broad native `Contact` access.
