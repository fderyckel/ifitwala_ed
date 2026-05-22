# Education Relationship CRM Documentation Index

Status: Canonical index
Code refs: None
Test refs: None

`ifitwala_ed/docs/relationship_crm/` is the canonical home for the education-native relationship CRM direction and contextual timeline projection rules.

The contracts in this folder define target behavior before Relationship CRM schema and runtime implementation. The admissions backend timeline endpoint and Inbox/Cockpit SPA timeline drawers are implemented; the planned Relationship CRM DocTypes, Relationship Timeline endpoint, and Relationship CRM SPA routes do not exist today.

Read in this order:

1. `01_education_relationship_crm_contract.md`
   product model, education terminology, domain boundaries, relationship categories, and implementation sequence
2. `02_contextual_timeline_contract.md`
   contextual timeline projection rules so users work from context instead of backend ledgers
3. `03_relationship_scope_and_visibility_contract.md`
   planned ownership, team, scope, privacy, and raw-contact-value rules

Canonical docs:

- `01_education_relationship_crm_contract.md` - planned target contract for `Education Relationship`, `Relationship Case`, `Relationship Activity`, and `Relationship Team`.
  Code refs: None for the planned Relationship CRM schema; related current refs are listed in the document.
  Test refs: None.
- `02_contextual_timeline_contract.md` - contract for admissions and relationship timeline projections over existing and future ledgers.
  Code refs: `ifitwala_ed/api/admissions_timeline.py`, `ifitwala_ed/ui-spa/src/components/admissions/AdmissionsTimelinePanel.vue`; related current refs are listed in the document.
  Test refs: `ifitwala_ed/api/test_admissions_timeline.py`, `ifitwala_ed/ui-spa/src/lib/services/admissions/__tests__/admissionsTimelineService.test.ts`.
- `03_relationship_scope_and_visibility_contract.md` - planned target contract for team ownership, tenant scope, contact governance, and role-limited visibility.
  Code refs: None for the planned Relationship CRM schema; related current refs are listed in the document.
  Test refs: None.

Related authority:

- `../security/contact_data_governance.md`
- `../admission/11_admissions_crm_contract.md`
- `../spa/17_admissions_inbox_contract.md`
- `../spa/07_org_communication_messaging_contract.md`
- `../high_concurrency_contract.md`
- `../nested_scope_contract.md`
