# Org Communication Messaging Contract (v1)

Status: Active

This document is the canonical messaging contract for all `Org Communication` comment, reaction, thread, and read-state workflows across staff, student, guardian, and admissions surfaces.

## 1. Canonical Model

Status: Implemented

Code refs:
- `ifitwala_ed/api/org_communication_interactions.py`
- `ifitwala_ed/api/admissions_communication.py`
- `ifitwala_ed/api/org_communication_archive.py`
- `ifitwala_ed/api/guardian_communications.py`
- `ifitwala_ed/api/file_access.py`
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/org_communication_archive.py`
- `ifitwala_ed/setup/doctype/communication_interaction_entry/communication_interaction_entry.py`
- `ifitwala_ed/students/doctype/portal_read_receipt/portal_read_receipt.py`

Test refs:
- `ifitwala_ed/api/test_org_communication_interactions.py`
- `ifitwala_ed/api/test_admissions_communication.py`
- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/ui-spa/src/lib/services/communicationInteraction/__tests__/communicationInteractionService.test.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCommunication/__tests__/guardianCommunicationService.test.ts`
- Patch coverage: None

Rules:

1. `Org Communication` is the thread/container truth.
2. `Communication Interaction Entry` is the only runtime ledger for reactions, comments, and thread rows.
3. `Portal Read Receipt` is the only runtime read-state ledger.
4. `Communication Interaction` is removed from the schema and runtime contract.
5. `Portal Read Receipt` is a generic cross-doctype read-state ledger. Surfaces may project it through domain-specific workflow APIs, but they must not invent parallel per-surface read-state tables for the same concern.

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
2. The resolved audience may include staff, students, and/or guardians depending on the communication configuration. It does not mean "outside the school" by default.
3. `Public to audience` means visible to the resolved recipients of that communication on supported surfaces. It does not mean public web visibility, open internet visibility, or cross-school visibility.
4. `allow_public_thread` means "allow recipient-visible shared audience thread entries" for that communication's resolved audience.
5. `allow_public_thread=0` is not a global "interactions off" switch. Depending on interaction mode, entries may still be accepted with school-side/private visibility.
6. `allow_private_notes` means school-side/private visibility rather than recipient-visible thread sharing.
7. Staff-facing surfaces must not treat `allow_public_thread` as the sole thread toggle. `Staff Comments` remains a staff thread, and `Student Q&A` remains available to staff even when recipient entries are private.
8. Recipient-facing `Student Q&A` with `allow_public_thread=1` is a shared audience thread.
9. Recipient-facing `Student Q&A` with `allow_public_thread=0` is a private note-to-school flow, not a missing-interactions state.
10. Recipient-facing `Structured Feedback` is a reaction/feedback mode and must not be presented as a generic comment thread.
11. `Student Q&A` does not support bare reaction-only submissions through `react_to_org_communication`; surfaces should route users into the question/comment flow instead of showing generic reaction affordances.

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
5. `get_org_communication_item` may expose attachment rows for archive/detail rendering, but governed file rows must be returned with server-owned action URLs such as `open_url`, optional `preview_url`, and optional `thumbnail_url`, never raw private paths.
6. Archive/detail surfaces may render inline image cards from `thumbnail_url` only; when that thumbnail is missing or fails to load, the SPA must keep the attachment in an action-led state instead of switching the inline image source to `preview_url` or the original file.
7. Full-width first-page PDF previews still come from `preview_url` only when `preview_status` reports a ready preview asset; link rows and non-ready PDFs must stay action-led rather than attempting generic web-page preview scraping.

## 3. Surface Matrix

Status: Partial

Code refs:
- `ifitwala_ed/ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/OrgCommunicationArchive.vue`
- `ifitwala_ed/ui-spa/src/components/activity/ActivityCommunicationPanel.vue`
- `ifitwala_ed/ui-spa/src/pages/student/StudentCommunicationCenter.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCommunicationCenter.vue`
- `ifitwala_ed/ui-spa/src/pages/student/StudentHome.vue`
- `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
- `ifitwala_ed/api/student_communications.py`
- `ifitwala_ed/api/guardian_communications.py`
- `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantMessages.vue`
- `ifitwala_ed/ui-spa/src/lib/services/communicationInteraction/communicationInteractionService.ts`
- `ifitwala_ed/ui-spa/src/lib/services/admissions/admissionsService.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCommunication/guardianCommunicationService.ts`

Test refs:
- `ifitwala_ed/ui-spa/src/lib/services/communicationInteraction/__tests__/communicationInteractionService.test.ts`
- `ifitwala_ed/ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCommunication/__tests__/guardianCommunicationService.test.ts`
- `ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentHome.test.ts`
- `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianCommunicationCenter.test.ts`
- `ifitwala_ed/api/test_student_communications.py`
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
6. Student-facing communication history surfaces read only `portal_surface='Portal Feed' | 'Everywhere'`; `Desk` and `Morning Brief` rows are staff-only surfaces even when audience scope overlaps.
7. Student Hub may surface bounded communication highlights, but the portal-wide student history is owned by `StudentCommunicationCenter.vue`.
8. `CourseDetail.vue` must not render inline class-message bodies; it may expose only a bounded `Class Updates` handoff into `StudentCommunicationCenter.vue` with the current `course_id` and `student_group` context applied.
9. Guardian-facing communication history surfaces read `portal_surface='Portal Feed' | 'Everywhere'` plus legacy `Guardian Portal` rows while that surface label remains in historical data.
10. Guardian activity communication panels and `/guardian/communications` use the shared interaction service.
11. `GuardianCommunicationCenter.vue` owns the guardian portal's family-wide org communication history and defaults to all linked children before any child filter is applied.
12. Guardian communication rows must render once per `Org Communication` with the matched linked-child labels attached; the page must not duplicate the same communication once per child.
13. Guardian communication center may render school-event rows in the same family feed, but only `Org Communication` rows use the shared messaging interaction and read-state workflows.
14. Applicant messages use the admissions service, which writes to the same canonical entry ledger.
15. No surface may call any retired `Communication Interaction` API or schema artifact.

## 4. Visibility and Read-State

Status: Implemented

Code refs:
- `ifitwala_ed/api/org_comm_utils.py`
- `ifitwala_ed/api/org_communication_interactions.py`
- `ifitwala_ed/api/student_communications.py`
- `ifitwala_ed/api/guardian_communications.py`
- `ifitwala_ed/api/admissions_communication.py`
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/file_access.py`

Test refs:
- `ifitwala_ed/api/test_org_comm_utils.py`
- `ifitwala_ed/api/test_org_communication_interactions.py`
- `ifitwala_ed/api/test_admissions_communication.py`
- `ifitwala_ed/api/test_guardian_phase2.py`
- Patch coverage: None

Rules:

1. Org Communication visibility is enforced server-side through `check_audience_match(...)`.
2. Audience matching supports `School Scope`, `Organization`, `Team`, and `Student Group`.
3. Student portal visibility for `Student Group` audiences matches active `Student Group Student` membership and still requires `to_students = 1`.
4. Student portal visibility for `School Scope` audiences matches the student anchor-school and active student-group school context; `Organization` rows remain unavailable to students.
5. Student communication history surfaces must additionally filter to `portal_surface='Portal Feed' | 'Everywhere'`.
6. Guardian portal visibility reuses the same audience matcher, but the server must hydrate the guardian's linked-student, student-group, school, and organization ancestry context before evaluating the communication row.
7. Guardian communication history surfaces must additionally filter to `portal_surface='Portal Feed' | 'Everywhere'` plus legacy `Guardian Portal`.
8. `Organization` rows may target guardians when `to_guardians = 1`; matching is based on the linked students' schools and their ancestor organizations.
9. Admissions visibility is enforced server-side through the `Student Applicant` context guard.
10. Guardian communication-center child filters may target only linked students; out-of-scope child filters must fail server-side instead of narrowing on the client.
11. Unread/read state is derived from `Portal Read Receipt`.
12. For guardian/activity summary logic, a user’s own interaction entry also counts as seen.
13. Hidden rows never contribute to threads, comment counts, or unread counts.
14. Staff archive and shared interaction endpoints may allow the `Org Communication.owner` to access their own authored communication when no explicit audience scope filter (`team`, `student_group`, `school`) is being enforced.
15. Org Communication attachment open routes must enforce the same audience visibility contract as archive detail, including owner visibility for authored history.
16. Staff archive `Academic Admin` visibility is school-cone first:
    - when `Employee.school` exists, visible school-scoped and student-group communications must stay within that school plus its descendant schools
    - descendant-organization fallback does not widen archive visibility beyond that school cone
17. Staff archive `Academic Admin` visibility falls back to organization scope only when no `Employee.school` is configured:
    - visible school-scoped and student-group communications may come from any school belonging to `Employee.organization` or its descendant organizations
    - organization-targeted staff rows may also resolve within that descendant-organization scope
18. Shared org-communication interaction endpoints (`summary`, `thread`, `react`, `comment`, `mark read`) must use the same effective academic-admin visibility context as archive/detail so a visible communication never becomes non-interactive solely because the user has no default school.
19. Within that effective scope, `Academic Admin` archive/detail and shared interaction visibility does not depend on recipient overlap (`to_staff` vs `to_students` / `to_guardians`); scoped student-group and school-scope communications remain readable and interactive for the admin lens.

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
- `ifitwala_ed/api/guardian_communications.py`
- `ifitwala_ed/api/guardian_home.py`
- `ifitwala_ed/api/org_communication_archive.py`
- `ifitwala_ed/ui-spa/src/lib/services/communicationInteraction/communicationInteractionService.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCommunication/guardianCommunicationService.ts`
- `ifitwala_ed/ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/OrgCommunicationArchive.vue`
- `ifitwala_ed/ui-spa/src/components/activity/ActivityCommunicationPanel.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianCommunicationCenter.vue`
- `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantMessages.vue`

Test refs:
- `ifitwala_ed/api/test_org_communication_interactions.py`
- `ifitwala_ed/api/test_admissions_communication.py`
- `ifitwala_ed/api/test_guardian_phase2.py`
- `ifitwala_ed/ui-spa/src/lib/services/communicationInteraction/__tests__/communicationInteractionService.test.ts`
- `ifitwala_ed/ui-spa/src/lib/services/guardianCommunication/__tests__/guardianCommunicationService.test.ts`
- `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianCommunicationCenter.test.ts`
- Patch coverage: None

| Concern | Canonical owner | Code refs | Test refs |
| --- | --- | --- | --- |
| Schema / DocType | `Org Communication`, `Communication Interaction Entry`, `Portal Read Receipt` | `setup/doctype/communication_interaction_entry/*`, `students/doctype/portal_read_receipt/*` | `api/test_org_communication_interactions.py` |
| Controller / workflow logic | Shared messaging workflow APIs, guardian communication-center bootstrap, and admissions wrappers | `api/org_communication_interactions.py`, `api/guardian_communications.py`, `api/admissions_communication.py` | `api/test_org_communication_interactions.py`, `api/test_guardian_phase2.py`, `api/test_admissions_communication.py` |
| API endpoints | Named interaction endpoints plus guardian communication-center bootstrap | `api/org_communication_interactions.py`, `api/guardian_communications.py`, `api/admissions_communication.py` | `api/test_org_communication_interactions.py`, `api/test_guardian_phase2.py`, `api/test_admissions_communication.py` |
| SPA/UI surfaces | Morning Brief, Archive, Student Communication Center, Guardian Communication Center, Activity panels, Applicant Messages | `ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue`, `ui-spa/src/pages/staff/OrgCommunicationArchive.vue`, `ui-spa/src/pages/student/StudentCommunicationCenter.vue`, `ui-spa/src/pages/guardian/GuardianCommunicationCenter.vue`, `ui-spa/src/components/activity/ActivityCommunicationPanel.vue`, `ui-spa/src/pages/admissions/ApplicantMessages.vue` | `ui-spa/src/lib/services/communicationInteraction/__tests__/communicationInteractionService.test.ts`, `ui-spa/src/lib/services/guardianCommunication/__tests__/guardianCommunicationService.test.ts`, `ui-spa/src/lib/services/student/__tests__/studentLearningHubService.test.ts`, `ui-spa/src/pages/guardian/__tests__/GuardianCommunicationCenter.test.ts` |
| Reports / dashboards / briefings | Morning Brief, Archive, Guardian Home unread summaries, Guardian Communication Center | `api/org_communication_archive.py`, `api/guardian_home.py`, `api/guardian_communications.py`, `ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue`, `ui-spa/src/pages/guardian/GuardianCommunicationCenter.vue` | `api/test_org_communication_interactions.py`, `api/test_guardian_phase2.py` |
| Scheduler / background jobs | None | None | None |
| Migration / retirement | Legacy snapshot rows backfilled in pre-sync; legacy schema removed in post-sync cleanup | `patches/setup/p01_migrate_communication_interactions_to_entry_ledger.py`, `patches/setup/p02_drop_communication_interaction_entry_legacy_link.py`, `patches/setup/p03_delete_communication_interaction_doctype.py`, `patches.txt` | None |
