# Org Communication Messaging Contract (v1)

Status: Active

This document is the canonical messaging contract for all `Org Communication` comment, reaction, thread, and read-state workflows across staff, student, guardian, and admissions surfaces.

## 1. Canonical Model

Status: Implemented

Code refs:
- `ifitwala_ed/api/org_communication_interactions.py`
- `ifitwala_ed/api/admissions_communication.py`
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/org_communication_archive.py`
- `ifitwala_ed/setup/doctype/communication_interaction_entry/communication_interaction_entry.py`
- `ifitwala_ed/students/doctype/portal_read_receipt/portal_read_receipt.py`

Test refs:
- `ifitwala_ed/api/test_org_communication_interactions.py`
- `ifitwala_ed/api/test_admissions_communication.py`
- `ifitwala_ed/ui-spa/src/lib/services/communicationInteraction/__tests__/communicationInteractionService.test.ts`
- Patch coverage: None

Rules:

1. `Org Communication` is the thread/container truth.
2. `Communication Interaction Entry` is the only runtime ledger for reactions, comments, and thread rows.
3. `Portal Read Receipt` is the only runtime read-state ledger.
4. `Communication Interaction` is removed from the schema and runtime contract.

## 2. Workflow APIs

Status: Implemented

Code refs:
- `ifitwala_ed/api/org_communication_interactions.py`
- `ifitwala_ed/api/admissions_communication.py`

Test refs:
- `ifitwala_ed/api/test_org_communication_interactions.py`
- `ifitwala_ed/api/test_admissions_communication.py`

Shared named workflow endpoints:

1. `get_org_communication_interaction_summary`
2. `get_org_communication_thread`
3. `react_to_org_communication`
4. `post_org_communication_comment`
5. `mark_org_communication_read`

Admissions-specific wrapper endpoints:

1. `get_admissions_case_thread`
2. `send_admissions_case_message`
3. `mark_admissions_case_thread_read`

Rules:

1. Clients must use named workflow endpoints only.
2. Clients must not assemble messaging behavior from generic CRUD calls.
3. Admissions endpoints remain context-specific wrappers over the same canonical entry/read-state model.

## 3. Surface Matrix

Status: Implemented

Code refs:
- `ifitwala_ed/ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/OrgCommunicationArchive.vue`
- `ifitwala_ed/ui-spa/src/components/activity/ActivityCommunicationPanel.vue`
- `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantMessages.vue`
- `ifitwala_ed/ui-spa/src/lib/services/communicationInteraction/communicationInteractionService.ts`
- `ifitwala_ed/ui-spa/src/lib/services/admissions/admissionsService.ts`

Test refs:
- `ifitwala_ed/ui-spa/src/lib/services/communicationInteraction/__tests__/communicationInteractionService.test.ts`
- Component-level tests: None

Rules:

1. Staff Morning Brief comments and reactions use the shared interaction service.
2. Staff Archive comments and reactions use the shared interaction service.
3. Student and guardian activity communication panels use the shared interaction service.
4. Applicant messages use the admissions service, which writes to the same canonical entry ledger.
5. No surface may call any retired `Communication Interaction` API or schema artifact.

## 4. Visibility and Read-State

Status: Implemented

Code refs:
- `ifitwala_ed/api/org_comm_utils.py`
- `ifitwala_ed/api/org_communication_interactions.py`
- `ifitwala_ed/api/admissions_communication.py`
- `ifitwala_ed/api/guardian_home.py`

Test refs:
- `ifitwala_ed/api/test_org_communication_interactions.py`
- `ifitwala_ed/api/test_admissions_communication.py`
- Patch coverage: None

Rules:

1. Org Communication visibility is enforced server-side through `check_audience_match(...)`.
2. Admissions visibility is enforced server-side through the `Student Applicant` context guard.
3. Unread/read state is derived from `Portal Read Receipt`.
4. For guardian/activity summary logic, a user’s own interaction entry also counts as seen.
5. Hidden rows never contribute to threads, comment counts, or unread counts.

## 5. Migration

Status: Implemented

Code refs:
- `ifitwala_ed/patches/setup/p01_migrate_communication_interactions_to_entry_ledger.py`
- `ifitwala_ed/patches.txt`

Test refs:
- Patch coverage: None

Rules:

1. Legacy `Communication Interaction` rows are backfilled into `Communication Interaction Entry` during migrate.
2. The patch is idempotent and skips rows already represented in the entry ledger.
3. The legacy link field on `Communication Interaction Entry` is dropped during the same migration.
4. The `Communication Interaction` DocType is deleted during the same migration.

## 6. Contract Matrix

Status: Implemented

Code refs:
- `ifitwala_ed/api/org_communication_interactions.py`
- `ifitwala_ed/api/admissions_communication.py`
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/org_communication_archive.py`
- `ifitwala_ed/ui-spa/src/lib/services/communicationInteraction/communicationInteractionService.ts`
- `ifitwala_ed/ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/OrgCommunicationArchive.vue`
- `ifitwala_ed/ui-spa/src/components/activity/ActivityCommunicationPanel.vue`
- `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantMessages.vue`

Test refs:
- `ifitwala_ed/api/test_org_communication_interactions.py`
- `ifitwala_ed/api/test_admissions_communication.py`
- `ifitwala_ed/ui-spa/src/lib/services/communicationInteraction/__tests__/communicationInteractionService.test.ts`
- Patch coverage: None

| Concern | Canonical owner | Code refs | Test refs |
| --- | --- | --- | --- |
| Schema / DocType | `Org Communication`, `Communication Interaction Entry`, `Portal Read Receipt` | `setup/doctype/communication_interaction_entry/*`, `students/doctype/portal_read_receipt/*` | `api/test_org_communication_interactions.py` |
| Controller / workflow logic | Shared messaging workflow APIs + admissions wrappers | `api/org_communication_interactions.py`, `api/admissions_communication.py` | `api/test_org_communication_interactions.py`, `api/test_admissions_communication.py` |
| API endpoints | Named interaction endpoints only | `api/org_communication_interactions.py`, `api/admissions_communication.py` | `api/test_org_communication_interactions.py`, `api/test_admissions_communication.py` |
| SPA/UI surfaces | Morning Brief, Archive, Activity panels, Applicant Messages | `ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue`, `ui-spa/src/pages/staff/OrgCommunicationArchive.vue`, `ui-spa/src/components/activity/ActivityCommunicationPanel.vue`, `ui-spa/src/pages/admissions/ApplicantMessages.vue` | `ui-spa/src/lib/services/communicationInteraction/__tests__/communicationInteractionService.test.ts` |
| Reports / dashboards / briefings | Morning Brief, Archive, Guardian Home unread summaries | `api/org_communication_archive.py`, `api/guardian_home.py`, `ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue` | `api/test_org_communication_interactions.py` |
| Scheduler / background jobs | None | None | None |
| Migration / retirement | Legacy snapshot rows backfilled and legacy schema removed | `patches/setup/p01_migrate_communication_interactions_to_entry_ledger.py`, `patches.txt` | None |
