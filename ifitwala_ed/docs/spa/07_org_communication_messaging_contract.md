# Org Communication Messaging Contract (v1)

Status: Active

This document is the canonical messaging contract for all `Org Communication` comment, reaction, thread, and read-state workflows across staff, student, guardian, and admissions surfaces.

## 1. Canonical Model

Status: Implemented

Code refs:
- `ifitwala_ed/api/org_communication_interactions.py`
- `ifitwala_ed/api/admissions_communication.py`
- `ifitwala_ed/api/org_communication_archive.py`
- `ifitwala_ed/api/file_access.py`
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

## 1.1 Audience and Visibility Terms

Status: Implemented

Code refs:
- `ifitwala_ed/api/org_comm_utils.py`
- `ifitwala_ed/api/org_communication_interactions.py`
- `ifitwala_ed/setup/doctype/communication_interaction_entry/communication_interaction_entry.py`
- `ifitwala_ed/ui-spa/src/components/communication/OrgCommunicationQuickCreateModal.vue`

Test refs:
- `ifitwala_ed/api/test_org_communication_interactions.py`
- `ifitwala_ed/api/test_admissions_communication.py`
- `ifitwala_ed/ui-spa/src/components/communication/__tests__/OrgCommunicationQuickCreateModal.test.ts`

Rules:

1. `Audience` means the recipients resolved for that communication by its audience rows and server-side visibility checks.
2. The resolved audience may include staff, students, guardians, and/or community recipients depending on the communication configuration. It does not mean "outside the school" by default.
3. `Public to audience` means visible to the resolved recipients of that communication on supported surfaces. It does not mean public web visibility, open internet visibility, or cross-school visibility.
4. `allow_public_thread` means "allow recipient-visible shared thread entries" for that communication's resolved audience.
5. `allow_public_thread=0` is not a global "interactions off" switch. Depending on interaction mode, entries may still be accepted with school-side/private visibility.
6. `allow_private_notes` means school-side/private visibility rather than recipient-visible thread sharing.
7. Staff-facing surfaces must not treat `allow_public_thread` as the sole comment toggle. For modes such as `Staff Comments` and staff-managed `Structured Feedback` / `Student Q&A`, staff thread access still follows the backend mode rules.
8. Recipient-facing surfaces still treat `allow_public_thread` as the shared-thread visibility toggle; school-side/private note workflows must not be presented as a generic shared comments button.
9. `Student Q&A` does not support bare reaction-only submissions through `react_to_org_communication`; surfaces should route users into the question/comment flow instead of showing generic reaction affordances.

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
4. `get_org_communication_item` must expose full-body HTML as `message_html`, not `message`, so the SPA transport envelope unwrapping cannot collide with the domain payload.
5. `get_org_communication_item` may expose attachment rows for archive/detail rendering, but governed file rows must be returned with server-owned `open_url` values instead of raw private paths.

## 3. Surface Matrix

Status: Partial

Code refs:
- `ifitwala_ed/ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/OrgCommunicationArchive.vue`
- `ifitwala_ed/ui-spa/src/components/activity/ActivityCommunicationPanel.vue`
- `ifitwala_ed/ui-spa/src/pages/student/StudentCommunicationCenter.vue`
- `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`
- `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
- `ifitwala_ed/api/student_communications.py`
- `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantMessages.vue`
- `ifitwala_ed/ui-spa/src/lib/services/communicationInteraction/communicationInteractionService.ts`
- `ifitwala_ed/ui-spa/src/lib/services/admissions/admissionsService.ts`

Test refs:
- `ifitwala_ed/ui-spa/src/lib/services/communicationInteraction/__tests__/communicationInteractionService.test.ts`
- `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts`
- `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentHome.test.ts`
- `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`
- Component-level tests: None

Rules:

1. Staff Morning Brief comments and reactions use the shared interaction service.
2. Staff Archive comments and reactions use the shared interaction service.
3. Staff Archive bootstrap defaults for `Academic Admin` come from the linked `Employee` record:
   - `organization = Employee.organization`
   - `school = Employee.school` when present
4. Staff Archive student-group filter options are constrained by the active school/org filter context:
   - selected school => only groups in that school
   - no selected school but selected organization => only groups in that organization-scoped school list
   - broader fallback => the archive context scope returned by `get_archive_context()`
5. Student activity communication panels and the student Communication Center use the shared interaction service.
6. Student Hub may surface bounded communication highlights, but the portal-wide student history is owned by `StudentCommunicationCenter.vue`.
7. `CourseDetail.vue` must not render inline class-message bodies; it may expose only a bounded `Class Updates` handoff into `StudentCommunicationCenter.vue` with the current `course_id` and `student_group` context applied.
8. Guardian activity communication panels use the shared interaction service, but a guardian-wide communication center is not implemented yet.
9. Applicant messages use the admissions service, which writes to the same canonical entry ledger.
10. No surface may call any retired `Communication Interaction` API or schema artifact.

## 4. Visibility and Read-State

Status: Implemented

Code refs:
- `ifitwala_ed/api/org_comm_utils.py`
- `ifitwala_ed/api/org_communication_interactions.py`
- `ifitwala_ed/api/student_communications.py`
- `ifitwala_ed/api/admissions_communication.py`
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/file_access.py`

Test refs:
- `ifitwala_ed/api/test_org_comm_utils.py`
- `ifitwala_ed/api/test_org_communication_interactions.py`
- `ifitwala_ed/api/test_admissions_communication.py`
- Patch coverage: None

Rules:

1. Org Communication visibility is enforced server-side through `check_audience_match(...)`.
2. Audience matching supports `School Scope`, `Organization`, `Team`, and `Student Group`.
3. Student portal visibility for `Student Group` audiences matches active `Student Group Student` membership and still requires `to_students = 1`.
4. Student portal visibility for `School Scope` audiences matches the student anchor-school and active student-group school context; `Organization` rows remain staff-only.
5. Admissions visibility is enforced server-side through the `Student Applicant` context guard.
6. Unread/read state is derived from `Portal Read Receipt`.
7. For guardian/activity summary logic, a user’s own interaction entry also counts as seen.
8. Hidden rows never contribute to threads, comment counts, or unread counts.
9. Staff archive and shared interaction endpoints may allow the `Org Communication.owner` to access their own authored communication when no explicit audience scope filter (`team`, `student_group`, `school`) is being enforced.
10. Org Communication attachment open routes must enforce the same audience visibility contract as archive detail, including owner visibility for authored history.
11. Staff archive `Academic Admin` visibility is school-cone first:
    - when `Employee.school` exists, visible school-scoped and student-group communications must stay within that school plus its descendant schools
    - descendant-organization fallback does not widen archive visibility beyond that school cone
12. Staff archive `Academic Admin` visibility falls back to organization scope only when no `Employee.school` is configured:
    - visible school-scoped and student-group communications may come from any school belonging to `Employee.organization` or its descendant organizations
    - organization-targeted staff rows may also resolve within that descendant-organization scope

## 5. Migration

Status: Implemented

Code refs:
- `ifitwala_ed/patches/setup/p01_migrate_communication_interactions_to_entry_ledger.py`
- `ifitwala_ed/patches/setup/p02_drop_communication_interaction_entry_legacy_link.py`
- `ifitwala_ed/patches/setup/p03_delete_communication_interaction_doctype.py`
- `ifitwala_ed/patches.txt`

Test refs:
- Patch coverage: None

Rules:

1. Legacy `Communication Interaction` rows are backfilled in the `pre_model_sync` migrate phase.
2. The backfill patch is idempotent and skips rows already represented in the entry ledger.
3. Legacy schema cleanup runs in dedicated `post_model_sync` patches after model sync.
4. The legacy link field on `Communication Interaction Entry` is dropped via a post-sync cleanup patch.
5. The `Communication Interaction` DocType is deleted via a post-sync cleanup patch.

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
| SPA/UI surfaces | Morning Brief, Archive, Student Communication Center, Activity panels, Applicant Messages | `ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue`, `ui-spa/src/pages/staff/OrgCommunicationArchive.vue`, `ui-spa/src/pages/student/StudentCommunicationCenter.vue`, `ui-spa/src/components/activity/ActivityCommunicationPanel.vue`, `ui-spa/src/pages/admissions/ApplicantMessages.vue` | `ui-spa/src/lib/services/communicationInteraction/__tests__/communicationInteractionService.test.ts`, `ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts` |
| Reports / dashboards / briefings | Morning Brief, Archive, Guardian Home unread summaries | `api/org_communication_archive.py`, `api/guardian_home.py`, `ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue` | `api/test_org_communication_interactions.py` |
| Scheduler / background jobs | None | None | None |
| Migration / retirement | Legacy snapshot rows backfilled in pre-sync; legacy schema removed in post-sync cleanup | `patches/setup/p01_migrate_communication_interactions_to_entry_ledger.py`, `patches/setup/p02_drop_communication_interaction_entry_legacy_link.py`, `patches/setup/p03_delete_communication_interaction_doctype.py`, `patches.txt` | None |
