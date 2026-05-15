# Cross-Portal Governed Attachment Preview Contract

Status: Canonical current runtime contract
Date: 2026-04-27
Code refs: `ifitwala_ed/api/file_access.py`, `ifitwala_ed/api/attachment_rows.py`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/api/gradebook_reads.py`, `ifitwala_ed/api/org_communication_attachments.py`, `ifitwala_ed/api/student_log_attachments.py`, `ifitwala_ed/api/org_communication_archive.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/task_submission.py`, `ifitwala_ed/api/teaching_plans_read_models.py`, `ifitwala_ed/api/student_log.py`, `ifitwala_ed/api/guardian_monitoring.py`, `ifitwala_ed/api/focus_context.py`, `ifitwala_ed/integrations/drive/admissions.py`, `ifitwala_ed/ui-spa/AGENTS.md`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`, `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantDocuments.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentLogs.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianMonitoring.vue`, `ifitwala_ed/ui-spa/src/overlays/student/StudentLogFollowUpOverlay.vue`
Test refs: `ifitwala_ed/api/test_attachment_rows.py`, `ifitwala_ed/api/test_file_access.py`, `ifitwala_ed/api/test_file_access_unit.py`, `ifitwala_ed/api/test_admissions_document_items.py`, `ifitwala_ed/api/test_gradebook.py`, `ifitwala_ed/api/test_materials.py`, `ifitwala_ed/api/test_org_communication_archive.py`, `ifitwala_ed/api/test_task_submission.py`, `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/students/doctype/student_log/test_student_log_evidence_unit.py`, `ifitwala_ed/ui-spa/src/components/tasks/__tests__/CreateTaskDeliveryOverlay.test.ts`
Related current-state docs:

- `ifitwala_ed/docs/high_concurrency_contract.md`
- `ifitwala_ed/docs/files_and_policies/files_06_org_communication_attachment_contract.md`
- `ifitwala_ed/docs/files_and_policies/files_07_education_file_semantics_and_cross_app_contract.md`
- `ifitwala_ed/docs/curriculum/03_curriculum_materials_and_resource_contract.md`
- `../ifitwala_drive/ifitwala_drive/docs/21_cross_portal_governed_attachment_preview_contract.md`

## Bottom Line

- Current runtime uses stable Ed-owned `open_url`, `preview_url`, and `thumbnail_url` fields instead of storage paths or bootstrap-time signed grants.
- Preview remains a business-surface contract owned by Ed authorization and DTO assembly, not a generic browser/file-system concern.
- Drive remains responsible for derivative generation and short-lived preview/download grants.
- Historical proposal/review sections below are retained for provenance, but the implemented-runtime sections in this note are the authority for new work.

## Current Implemented Baseline

Status: Implemented current-state baseline
Code refs: `ifitwala_ed/api/file_access.py`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/api/org_communication_attachments.py`, `ifitwala_ed/api/student_log_attachments.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans_read_models.py`, `ifitwala_ed/api/student_log.py`, `ifitwala_ed/api/guardian_monitoring.py`, `ifitwala_ed/api/focus_context.py`, `ifitwala_ed/integrations/drive/admissions.py`, `ifitwala_ed/ui-spa/src/components/attachments/AttachmentPreviewCard.vue`, `ifitwala_ed/ui-spa/src/components/communication/CommunicationAttachmentPreviewList.vue`, `ifitwala_ed/ui-spa/src/components/planning/PlanningResourcePanel.vue`, `ifitwala_ed/ui-spa/src/components/learning/StudentLearningResourceCard.vue`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookStudentDrawer.vue`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/student/StudentLogs.vue`, `ifitwala_ed/ui-spa/src/pages/guardian/GuardianMonitoring.vue`, `ifitwala_ed/ui-spa/src/overlays/student/StudentLogFollowUpOverlay.vue`
Test refs: `ifitwala_ed/api/test_file_access.py`, `ifitwala_ed/api/test_file_access_unit.py`, `ifitwala_ed/api/test_admissions_document_items.py`, `ifitwala_ed/api/test_materials.py`, `ifitwala_ed/api/test_org_communication_archive.py`, `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/students/doctype/student_log/test_student_log_evidence_unit.py`, `ifitwala_ed/ui-spa/src/components/attachments/__tests__/AttachmentPreviewCard.test.ts`, `ifitwala_ed/ui-spa/src/components/communication/__tests__/CommunicationAttachmentPreviewList.test.ts`, `ifitwala_ed/ui-spa/src/components/planning/__tests__/PlanningResourcePanel.test.ts`, `ifitwala_ed/ui-spa/src/components/tasks/__tests__/CreateTaskDeliveryOverlay.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/OrgCommunicationArchive.test.ts`, `ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianCommunicationCenter.test.ts`

Today Ifitwala_Ed already enforces the correct broad shape for governed reads:

- business surfaces return server-owned `open_url` values instead of raw private paths
- `open_org_communication_attachment(...)` re-checks communication visibility, then resolves a Drive grant just in time
- governed open/preview routes now fail closed when no safe public/external/Drive target exists; when the resolved Drive/local target is an in-site private path, Ed serves it inline instead of redirecting the browser to a raw `/private/...` URL
- Org Communication rows now also expose a stable `preview_url` route owned by Ed plus a `preview_status` hint for renderability
- Student Log evidence rows use the `student_log.evidence_attachment` workflow and expose stable Ed-owned `open_url`, `preview_url`, `thumbnail_url`, and nested `attachment_preview` DTOs on staff focus, student portal, and guardian monitoring surfaces
- staff, student, and guardian communication detail surfaces now render inline image previews plus small first-page PDF card previews from `thumbnail_url`, keep `preview_url` as the richer preview action, and still degrade to clean fallback cards when those governed routes are not ready
- the staff task creation overlay now lets teachers queue task attachments during task composition and uses the shared preview card for current task attachments when a created task remains open for attachment recovery
- planning-material surfaces now also expose stable `preview_url` routes for governed file resources in the staff course-plan and class-planning workspaces
- planning-material preview and thumbnail routes now resolve governed grants through a material-scoped Drive wrapper after Ed authorizes the placement/material context, so `Material Placement` visibility no longer depends on direct `Supporting Material` DocType read permission
- admissions open, preview, and thumbnail routes now resolve governed grants through an admissions-scoped Drive wrapper after Ed authorizes the applicant/family/staff context, so admissions portal reads do not depend on broad `Student Applicant` DocPerm
- the student learning space now also exposes stable `preview_url` routes for governed file resources on `CourseDetail.vue`
- current target surfaces now consume the nested `attachment_preview` DTO through one shared display-only SPA card layer, with thin communication, planning, student-learning, and evidence adapters around it
- student task attachments now render inside the assigned-work brief through the shared learning attachment card, with preview and download actions driven by the governed preview DTO
- upload/finalize responses for applicant documents now return the same stable post-upload attachment DTO shape immediately, so the SPA can update the row without reloading or guessing file URLs
- when Drive reports a preview status other than `ready`, Ed DTOs must keep `open_url` as the fallback action and suppress `preview_url` / `thumbnail_url`; users should never receive a preview action that is known to be pending, failed, unsupported, or not applicable
- the SPA does not need to know storage paths or Drive object keys

What still does not exist yet:

- a top-level shared cross-portal attachment preview row contract across all surfaces
- broad Ed-owned preview routes for all governed surfaces
- one fully unified list / gallery / drawer system across every governed preview surface

Drive now has a narrow image plus first-page PDF derivative foundation, but Ed should still treat preview as partial rollout:

- Org Communication currently points `thumbnail_url` at the richer governed preview route once Drive reports `preview_status = ready`, so inline image and PDF cards render the larger preview asset directly instead of the smaller dedicated thumbnail derivative; when preview is not ready, surfaces still fall back to compact metadata cards
- admissions applicant document surfaces and staff admissions review/readiness surfaces now also return stable `open_url`, `preview_url`, `thumbnail_url`, and nested `attachment_preview` DTOs for governed applicant evidence
- the staff task creation overlay can use `preview_url` where Drive reports a ready preview, while still keeping task-material actions inside the existing create flow
- staff planning-material surfaces can use `thumbnail_url` for inline image/PDF card previews and keep `preview_url` for richer preview actions
- the student learning space can use `thumbnail_url` for inline image/PDF card previews where Drive reports the card derivative ready, keep `preview_url` for richer preview actions, and keep `open_url` explicit while assigned-work attachments use the same governed preview DTO
- the task-submission evidence surface now returns stable `preview_url` and `open_url` values for selected submission attachments, with version summaries remaining bounded inside the gradebook drawer contract
- Student Log evidence uses attachment-level portal visibility flags in addition to the parent log visibility flags; staff read follows the Student Log visibility predicate, while student and guardian reads only surface rows explicitly shared to that portal audience
- other surfaces should still be treated as open/download-only until their stable preview routes exist

## Historical Review Notes

Status: Review result
Code refs: `ifitwala_ed/api/file_access.py`, `ifitwala_ed/api/org_communication_attachments.py`, `ifitwala_ed/ui-spa/AGENTS.md`
Test refs: `ifitwala_ed/api/test_file_access.py`, `ifitwala_ed/api/test_org_communication_archive.py`

What is correct and should be kept:

- preview is a governed business-surface read capability, not a generic file read
- Ifitwala_Ed owns attachment selection, portal-aware authorization, action policy, and DTO assembly
- shared SPA components should stay rendering-only
- surface-owned read models are the correct portal contract
- the same underlying file may be visible on one surface and absent on another

What must change before the architecture is locked:

- `thumbnail_url`, `preview_url`, `open_url`, and `download_url` must be stable server-owned action URLs or `null`, not provider-signed URLs issued during page bootstrap
- Ed portal clients must not call `ifitwala_drive.api.access.issue_preview_grant` or `issue_download_grant` directly; Ed must remain the surface permission gate
- the proposal should not imply one new HTTP endpoint per attachment use case if an existing aggregate page-init endpoint can include attachments without causing waterfalls
- preview rollout must be additive to current `open_url` contracts; no surface should regress while derivative preview is still partial
- preview permission and download permission must remain independently expressible; `can_preview` does not imply `can_download`

## Canonical Ed Ownership

Status: Implemented ownership rule
Code refs: `ifitwala_ed/api/file_access.py`, `ifitwala_ed/api/org_communication_archive.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans_read_models.py`
Test refs: `ifitwala_ed/api/test_file_access.py`, `ifitwala_ed/api/test_org_communication_archive.py`, `ifitwala_ed/api/test_teaching_plans.py`

Ifitwala_Ed owns:

- deciding which governed attachments belong on a business surface
- filtering those attachments for the current viewer in staff, student, or guardian context
- deciding whether preview, open, download, or delete actions are available on that surface
- returning surface labels, badges, grouping, and version context
- exposing stable action URLs that re-check the business surface before requesting Drive delivery grants

Ifitwala_Ed does not own:

- derivative generation
- derivative storage
- preview blob lifecycle
- object-storage URL construction

Rule:

> A portal preview is valid only when the viewer is authorized to read the owning business surface in that portal context.

## Stable URL Contract

Status: Implemented current contract
Code refs: `ifitwala_ed/api/file_access.py`
Test refs: `ifitwala_ed/api/test_file_access.py`

For cross-portal Ed surfaces, attachment DTO URL fields must be stable application-owned URLs or `null`.

Stable route contract means:

- stable Ed route shape
- not stable raw file location
- not stable cached permanent access URL

They may point to:

- Ed endpoints that validate surface access and then redirect to a Drive grant
- Drive-owned public or already-governed URLs only when the asset is intentionally public and the surface contract allows it

They must not be:

- raw `/private/...` paths
- provider object URLs
- short-lived signed URLs embedded in cached or bootstrap DTO payloads

Why this is locked:

- bootstrap/read-model payloads should stay cacheable and long enough to survive real user interaction
- short-lived delivery grants should be issued just in time, not at page load
- current Ed governed file access already follows this pattern and should remain the migration baseline
- the underlying Drive delivery grant is still short-lived and must be resolved at request time

## Thumbnail And Cache Direction

Status: Proposed target refinement
Code refs: `ifitwala_ed/api/file_access.py`, `ifitwala_ed/api/org_communication_attachments.py`, `ifitwala_ed/api/teaching_plans_read_models.py`, `ifitwala_ed/ui-spa/src/components/communication/CommunicationAttachmentPreviewList.vue`, `ifitwala_ed/ui-spa/src/components/planning/PlanningResourcePanel.vue`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`
Test refs: `ifitwala_ed/api/test_file_access.py`, `ifitwala_ed/api/test_file_access_unit.py`, `ifitwala_ed/ui-spa/src/components/communication/__tests__/CommunicationAttachmentPreviewList.test.ts`

Current pain point:

- Org Communication now prefers `thumbnail_url` for inline card previews, but that field currently resolves to the same governed preview route as `preview_url` once the richer preview derivative is ready
- governed attachment-card surfaces now use the Ed-owned `thumbnail_url` route for card-sized inline previews; compact avatar/profile-image derivative choices remain an internal Drive/Ed implementation detail
- governed applicant-document and staff admissions review DTOs now expose the same split, even where the first UI cut still uses explicit open actions instead of inline cards
- those preview routes are authorization-first Ed action routes, not dedicated thumbnail-delivery contracts
- the proposal should not "cache page bootstrap grants"; it should split thumbnail delivery from richer preview delivery while keeping Ed as the permission gate

Refined direction:

- add an additive `thumbnail_url` field for governed file DTOs
- `thumbnail_url` is for inline card/list previews and should be omitted until the requested card-sized derivative is actually ready
- `preview_url` remains the richer preview action
- `open_url` remains the original-file compatibility baseline and explicit fallback
- image and PDF card surfaces may fall back to `preview_url` inline when `thumbnail_url` is absent or when the thumbnail delivery route fails, so a missing card derivative does not blank the whole card while Drive catches up
- if Drive determines that an explicit card derivative is stale for the current version/render spec, Ed thumbnail routes should treat it the same as missing and let the SPA fall back to `preview_url` instead of serving an undersized legacy artifact
- Ed-owned thumbnail routes may use short-lived `frappe.cache()` entries for resolved redirect targets only, never for raw file bytes and never for DTO-embedded provider URLs
- cache keys must include at least `drive_file`, current version identity, the internal preview variant, and the relevant surface/context dimensions so tenant and portal scope cannot leak
- cache TTL must stay shorter than the underlying Drive grant lifetime

Initial rollout target:

- Org Communication archive/detail image cards first
- planning-material surfaces second via the shared `PlanningResourcePanel.vue` path that covers course-plan, unit-plan, and class-planning resource cards
- task-material image cards can follow after the same contract is stable on those two higher-value surfaces

## Shared DTO Direction

Status: Phase 7 in progress; top-level row contract implemented for applicant-facing admissions documents, staff planning resources, Org Communication attachments, staff task materials, and task submission evidence
Code refs: `ifitwala_ed/api/attachment_previews.py`, `ifitwala_ed/api/attachment_rows.py`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/api/org_communication_attachments.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans_read_models.py`, `ifitwala_ed/api/teaching_plans_staff.py`, `ifitwala_ed/api/task_submission.py`, `ifitwala_ed/api/released_feedback.py`, `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantDocuments.vue`, `ifitwala_ed/ui-spa/src/components/planning/PlanningResourcePanel.vue`, `ifitwala_ed/ui-spa/src/components/communication/CommunicationAttachmentPreviewList.vue`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookStudentDrawer.vue`, `ifitwala_ed/ui-spa/src/pages/staff/gradebook/components/GradebookPdfWorkspace.vue`
Test refs: `ifitwala_ed/api/test_attachment_previews.py`, `ifitwala_ed/api/test_attachment_rows.py`, `ifitwala_ed/api/test_admissions_document_items.py`, `ifitwala_ed/api/test_gradebook.py`, `ifitwala_ed/api/test_materials.py`, `ifitwala_ed/api/test_org_communication_attachments_unit.py`, `ifitwala_ed/api/test_org_communication_archive.py`, `ifitwala_ed/api/test_released_feedback.py`, `ifitwala_ed/api/test_task_submission_unit.py`, `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/ui-spa/src/components/planning/__tests__/PlanningResourcePanel.test.ts`, `ifitwala_ed/ui-spa/src/components/communication/__tests__/CommunicationAttachmentPreviewList.test.ts`, `ifitwala_ed/ui-spa/src/components/tasks/__tests__/CreateTaskDeliveryOverlay.test.ts`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`, `ifitwala_ed/ui-spa/src/pages/staff/__tests__/Gradebook.test.ts`

The shared DTO is now implemented in two layers:

- `AttachmentPreviewItem` is the existing display DTO consumed by the shared SPA card.
- `GovernedAttachmentRow` is the Phase 7 top-level surface row. It adds `id` and `surface` to the display DTO and is returned directly as `attachment` by migrated surfaces.

Applicant-facing admissions documents are the first migrated surface. Staff planning resources rendered through `PlanningResourcePanel.vue` are the second migrated surface. Org Communication attachments rendered through `CommunicationAttachmentPreviewList.vue` are the third migrated surface. Staff task materials rendered through `CreateTaskDeliveryOverlay.vue` are the fourth migrated surface. Task submission evidence rendered through the student course task view, staff gradebook drawer, and released-feedback document preview is the fifth migrated surface. Migrated payloads expose `attachment` directly and no longer expose the legacy nested `attachment_preview` adapter for that surface. Other surfaces remain additive until migrated one by one; when a surface migrates, its legacy adapter must be removed in the same change.

```ts
export type AttachmentPreviewItem = {
  item_id: string
  owner_doctype: string
  owner_name: string

  file_id: string | null
  link_url: string | null

  display_name: string
  description: string | null

  mime_type: string | null
  extension: string | null
  size_bytes: number | null

  kind:
    | 'image'
    | 'pdf'
    | 'video'
    | 'audio'
    | 'text'
    | 'office'
    | 'archive'
    | 'link'
    | 'other'

  preview_mode:
    | 'inline_image'
    | 'thumbnail_image'
    | 'pdf_embed'
    | 'media_player'
    | 'icon_only'
    | 'external_link'

  preview_status:
    | 'pending'
    | 'ready'
    | 'failed'
    | 'unsupported'
    | 'not_applicable'
    | null

  thumbnail_url: string | null
  preview_url: string | null
  open_url: string | null
  download_url: string | null

  width: number | null
  height: number | null
  page_count: number | null
  duration_seconds: number | null

  can_preview: boolean
  can_open: boolean
  can_download: boolean
  can_delete: boolean

  is_latest_version: boolean
  version_label: string | null

  badge: string | null
  source_label: string | null
  created_at: string | null
  created_by_label: string | null
}
```

DTO rules:

- URL fields are stable server-owned surface actions or `null`
- the DTO is already filtered for the current viewer; the SPA must not infer hidden attachments
- migrated Phase 7 surfaces expose `attachment: GovernedAttachmentRow | null`, not `attachment_preview`
- `thumbnail_url` should stay optional and represent the card-sized preview action for images or first-page PDF cards; DTOs must not expose Drive derivative role names or derivative-role query parameters
- `preview_url` should be used only when a richer preview action exists and `preview_status` is absent or `ready`
- `open_url` remains the current compatibility baseline during rollout
- a non-ready preview status must degrade to open-only actions rather than surfacing a failing preview button
- current surfaces may still keep their legacy top-level fields (`kind`, `material_type`, `title`, `reference_url`, and similar) while also exposing the nested shared DTO during convergence

## Phase 5 UX Friction Rule

Status: Implemented current target rule for active governed attachment surfaces
Code refs: `ifitwala_ed/api/attachment_previews.py`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/api/org_communication_attachments.py`, `ifitwala_ed/api/task_submission.py`, `ifitwala_ed/students/doctype/student_log/evidence.py`
Test refs: `ifitwala_ed/api/test_attachment_previews.py`, `ifitwala_ed/api/test_admissions_document_items.py`, `ifitwala_ed/api/test_org_communication_attachments_unit.py`, `ifitwala_ed/api/test_task_submission_unit.py`, `ifitwala_ed/students/doctype/student_log/test_student_log_evidence_unit.py`

For every governed file surface:

- provide one obvious upload action in the owning workflow surface
- return a stable post-upload DTO immediately after successful finalize
- show actionable upload/finalize errors from the server rather than swallowing them in the SPA
- expose only stable `open_url`, optional `thumbnail_url`, and optional `preview_url`
- treat `open_url` as the guaranteed fallback whenever preview generation is not ready or cannot apply
- keep preview/open behavior consistent across staff, student, guardian, and admissions surfaces by consuming the shared attachment display object for each migrated or additive surface

## Surface Endpoint Rule

Status: Implemented for active governed attachment surfaces; still binding for future surfaces
Code refs: `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/api/org_communication_archive.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/docs/high_concurrency_contract.md`
Test refs: `ifitwala_ed/api/test_admissions_document_items.py`, `ifitwala_ed/api/test_file_access_unit.py`, `ifitwala_ed/api/test_org_communication_archive.py`, `ifitwala_ed/api/test_teaching_plans.py`

The correct Ed contract is surface-owned read models, not a generic file-preview API.

Allowed patterns:

- existing aggregate page-init endpoints include `AttachmentPreviewItem[]`
- a dedicated surface attachment endpoint exists only when the surface is independently loaded and remains bounded

Forbidden patterns:

- one request per attachment
- a generic cross-portal `get_file_preview(file_id)` as the main portal contract
- SPA-side permission inference

Examples of acceptable surface owners:

- admissions applicant-document list/upload responses
- org communication archive/detail
- staff Morning Brief announcement detail, which consumes the same org-communication attachment DTO and must resolve preview/open routes from the governed attachment slot rather than from a compatibility `File` lookup
- student learning space resource shelves
- future task-submission review detail
- future guardian-facing reporting/document surfaces

Current Phase 6 guard:

- active read models must batch Drive attachment rows, thumbnail readiness, and MIME/version metadata once per surface payload instead of resolving one attachment per request

## Portal Authorization Rule

Status: Implemented for active governed attachment routes; still binding for future routes
Code refs: `ifitwala_ed/api/file_access.py`, `ifitwala_ed/integrations/drive/admissions.py`, `ifitwala_ed/api/org_comm_utils.py`, `ifitwala_ed/curriculum/materials.py`
Test refs: `ifitwala_ed/api/test_file_access.py`, `ifitwala_ed/api/test_file_access_unit.py`, `ifitwala_ed/api/test_org_communication_archive.py`, `ifitwala_ed/api/test_teaching_plans.py`

Authorization remains surface-specific and server-side:

- staff access follows the owning workflow and operational permissions
- student access is limited to student-visible records and released artifacts
- guardian access is limited to guardian-authorized family/student surfaces with no sibling leakage unless explicitly documented
- admissions access follows explicit applicant, family, scoped staff, and review business authorization; broad `Student Applicant` DocPerm must not be required for portal file reads
- Drive grant services for Ed-owned surfaces must call the matching Ed surface delegate before resolving the Drive File; generic Drive owner DocPerm checks are not the admissions portal contract

The frontend is presentation only. It must never widen or infer access.

## Cross-App Implementation Plan

Status: Implemented through Phase 6 for active governed attachment surfaces
Code refs: `ifitwala_ed/api/file_access.py`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/api/org_communication_archive.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans.py`
Test refs: `ifitwala_ed/api/test_file_access.py`, `ifitwala_ed/api/test_file_access_unit.py`, `ifitwala_ed/api/test_admissions_document_items.py`, `ifitwala_ed/api/test_org_communication_archive.py`, `ifitwala_ed/api/test_teaching_plans.py`

Phase 1: documentation and contract lock - implemented

- keep current `open_url` behavior as baseline
- lock the Ed/Drive ownership split in canonical docs in both repos
- forbid portal-direct Drive grant calls for Ed-owned surfaces
- keep Phase 1 media scope narrow: image preview plus first-page PDF preview, no broad media ambitions

Phase 2: Drive dependency foundation - implemented for the narrow image/PDF scope

- use the existing Drive image/PDF derivative lifecycle and derivative-role grant resolution as the first foundation
- keep wider media support beyond images and first-page PDFs deferred until the narrow path is stable

Phase 3: Ed service foundation - implemented for active governed surfaces

- add a shared Ed attachment preview builder service
- add stable thumbnail/preview/open/download routes that re-check surface authorization and then resolve Drive grants
- allow short-lived Ed-side caching only for resolved thumbnail redirect targets; do not embed provider grant URLs in bootstrap DTOs
- keep route ownership explicit by surface or shared Ed file-access helpers

Phase 4: shared SPA layer - implemented additively

- add display-only attachment preview components and local interaction composables
- lazy load rich previews; do not dominate routed pages with giant viewers

Phase 5: rollout order - implemented for current active target surfaces

- Org Communication first
- supporting-material planning surfaces next, specifically course-plan, unit-plan, and class-planning cards via the existing shared planning resource panel
- task materials after the planning surface contract is stable
- task submissions, feedback, and stricter version-aware evidence surfaces after the foundation is stable

Phase 6: regression protection - implemented for active governed attachment surfaces

- add permission-matrix tests per surface
- add route tests for preview/open/download behaviors
- validate that page-init remains bounded and does not introduce attachment waterfalls
- admissions specifically locks download, preview, and thumbnail routes to the admissions-scoped Drive grant wrappers, plus applicant/family/staff/reviewer business authorization
- admissions applicant-document listing locks Drive attachment row lookup, thumbnail readiness, and MIME/version lookup to batched surface reads

Remaining items are future scope, not unfinished Phase 6 work: the top-level shared row contract across all surfaces, broad preview routes for every governed file surface, and one unified gallery/drawer system.

## Phase 7 Attachment Convergence

Status: Approved and in progress
Code refs: `ifitwala_ed/api/attachment_rows.py`, `ifitwala_ed/api/admissions_portal.py`, `ifitwala_ed/api/org_communication_attachments.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans_read_models.py`, `ifitwala_ed/api/teaching_plans_staff.py`, `ifitwala_ed/ui-spa/src/types/contracts/attachments/shared.ts`, `ifitwala_ed/ui-spa/src/types/contracts/org_communication_attachments/shared.ts`, `ifitwala_ed/ui-spa/src/types/contracts/staff_teaching/get_staff_class_planning_surface.ts`, `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantDocuments.vue`, `ifitwala_ed/ui-spa/src/components/planning/PlanningResourcePanel.vue`, `ifitwala_ed/ui-spa/src/components/communication/CommunicationAttachmentPreviewList.vue`, `ifitwala_ed/ui-spa/src/components/tasks/CreateTaskDeliveryOverlay.vue`
Test refs: `ifitwala_ed/api/test_attachment_rows.py`, `ifitwala_ed/api/test_admissions_document_items.py`, `ifitwala_ed/api/test_materials.py`, `ifitwala_ed/api/test_org_communication_archive.py`, `ifitwala_ed/api/test_org_communication_attachments_unit.py`, `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/ui-spa/src/lib/services/admissions/__tests__/admissionsService.test.ts`, `ifitwala_ed/ui-spa/src/components/planning/__tests__/PlanningResourcePanel.test.ts`, `ifitwala_ed/ui-spa/src/components/communication/__tests__/CommunicationAttachmentPreviewList.test.ts`, `ifitwala_ed/ui-spa/src/components/tasks/__tests__/CreateTaskDeliveryOverlay.test.ts`

Rules:

- migrate one surface at a time
- return `attachment: GovernedAttachmentRow | null` directly on migrated surface rows
- remove that surface's legacy nested `attachment_preview` adapter in the same change
- do not add a generic file-preview endpoint, file browser, or SPA permission inference layer
- keep each surface's existing aggregate read endpoint bounded; no attachment waterfalls
- do not widen media preview support until Drive has deterministic derivative/status support for that media class

First migrated surface:

- applicant-facing Admissions Documents page
- server list/upload endpoints return top-level `attachment`
- `ApplicantDocuments.vue` renders the shared preview card from `item.attachment`
- the legacy `item.attachment_preview` adapter is removed for that surface

Second migrated surface:

- staff planning resource cards rendered by `PlanningResourcePanel.vue`
- staff class-planning and course-plan resource read payloads return top-level `attachment` for Course Plan, Unit Plan, Class Teaching Plan, and Class Session materials
- create/upload planning-resource mutation responses return `resource.attachment`
- `PlanningResourcePanel.vue` renders the shared preview card from `resource.attachment`
- the legacy `resource.attachment_preview` adapter is removed for that surface

Third migrated surface:

- Org Communication attachment cards rendered by `CommunicationAttachmentPreviewList.vue`
- staff archive/detail, student communication center, and guardian communication center receive communication attachment rows with top-level `attachment`
- Org Communication file/link row DTOs no longer duplicate `open_url`, `preview_url`, `thumbnail_url`, or `preview_status` outside the governed attachment row
- `CommunicationAttachmentPreviewList.vue` renders the shared preview card from `attachment.attachment`
- the legacy `attachment.attachment_preview` adapter is removed for that surface

Fourth migrated surface:

- staff task-material cards rendered by `CreateTaskDeliveryOverlay.vue`
- task-material list, link-create, and file-upload responses return `attachment`
- task-material rows no longer duplicate `open_url`, `preview_url`, `thumbnail_url`, or `file` outside the governed attachment row
- `CreateTaskDeliveryOverlay.vue` renders the shared preview card from `material.attachment`
- the legacy `material.attachment_preview` adapter is removed for that surface

Fifth migrated surface:

- task submission evidence attachments rendered through student latest-submission, staff gradebook drawer, and released-feedback document preview surfaces
- task submission evidence read payloads return `attachment`
- task submission attachment rows no longer duplicate `open_url`, `preview_url`, `thumbnail_url`, `preview_status`, or `file` outside the governed attachment row
- student and staff surfaces render from `submissionAttachment.attachment`; PDF annotation readiness reads the same governed row values
- the legacy `submissionAttachment.attachment_preview` adapter is removed for that surface

## Important Non-Goals

Status: Locked for this proposal
Code refs: `ifitwala_ed/ui-spa/AGENTS.md`, `ifitwala_ed/docs/high_concurrency_contract.md`
Test refs: None

This proposal does not authorize:

- a generic end-user file browser inside Ed
- client construction of storage or private file URLs
- Office conversion scope in Phase 1
- replacing all current governed file-open routes in one pass
- portal contracts that depend on expiring provider URLs embedded at page bootstrap time
- aggressive idle-time deletion of current-version preview derivatives in Phase 1; cleanup should focus first on stale replaced derivatives plus deterministic erasure cleanup
