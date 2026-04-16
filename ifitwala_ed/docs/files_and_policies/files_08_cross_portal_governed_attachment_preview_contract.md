# Cross-Portal Governed Attachment Preview Contract

Status: Proposed canonical contract for cross-app implementation
Date: 2026-04-16
Code refs: `ifitwala_ed/api/file_access.py`, `ifitwala_ed/api/org_communication_attachments.py`, `ifitwala_ed/api/org_communication_archive.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans_read_models.py`, `ifitwala_ed/ui-spa/AGENTS.md`
Test refs: `ifitwala_ed/api/test_file_access.py`, `ifitwala_ed/api/test_org_communication_archive.py`, `ifitwala_ed/api/test_teaching_plans.py`
Related current-state docs:

- `ifitwala_ed/docs/high_concurrency_contract.md`
- `ifitwala_ed/docs/files_and_policies/files_06_org_communication_attachment_contract.md`
- `ifitwala_ed/docs/files_and_policies/files_07_education_file_semantics_and_cross_app_contract.md`
- `ifitwala_ed/docs/curriculum/03_curriculum_materials_and_resource_contract.md`
- `../ifitwala_drive/ifitwala_drive/docs/21_cross_portal_governed_attachment_preview_contract.md`

## Bottom Line

- The proposal is directionally correct and matches the locked Ed/Drive split.
- Do not over-model Phase 1. Image preview, optional PDF preview, clean status handling, and Org Communication first are enough.
- The main correction is contract shape: cross-portal DTOs must carry stable server-owned action URLs, not pre-issued short-lived Drive grants.
- Preview belongs in surface-owned Ed read models and authorization rules, not in a generic file browser or direct portal calls to Drive grant APIs.
- Current `open_url` behavior remains the production baseline until derivative preview infrastructure exists in Drive and Ed routes are added deliberately.

## Current Implemented Baseline

Status: Implemented current-state baseline
Code refs: `ifitwala_ed/api/file_access.py`, `ifitwala_ed/api/org_communication_attachments.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans_read_models.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`, `ifitwala_ed/ui-spa/src/components/learning/StudentLearningResourceCard.vue`
Test refs: `ifitwala_ed/api/test_file_access.py`, `ifitwala_ed/api/test_org_communication_archive.py`, `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts`

Today Ifitwala_Ed already enforces the correct broad shape for governed reads:

- business surfaces return server-owned `open_url` values instead of raw private paths
- `open_org_communication_attachment(...)` re-checks communication visibility, then resolves a Drive grant just in time
- Org Communication rows now also expose a stable `preview_url` route owned by Ed
- planning-material surfaces now also expose stable `preview_url` routes for governed file resources in the staff course-plan and class-planning workspaces
- the student learning space now also exposes stable `preview_url` routes for governed file resources on `CourseDetail.vue`
- student task-material chips remain lightweight, but they also prefer `preview_url` over `open_url` when preview is available
- the SPA does not need to know storage paths or Drive object keys

What still does not exist yet:

- a shared cross-portal attachment preview DTO
- broad Ed-owned preview routes for all governed surfaces
- a shared SPA preview layer across the target surfaces

Drive now has a narrow image-derivative foundation, but Ed should still treat preview as partial rollout:

- Org Communication can use `preview_url` where Drive reports a ready preview
- staff planning-material surfaces can use `preview_url` where Drive reports a ready preview
- the student learning space can use `preview_url` where Drive reports a ready preview, while still keeping `open_url` explicit
- other surfaces should still be treated as open/download-only until their stable preview routes exist

## Assessment Of The Proposal

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

Status: Proposed target contract
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

Status: Proposed target contract
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

## Shared DTO Direction

Status: Proposed target contract
Code refs: `ifitwala_ed/api/org_communication_attachments.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans_read_models.py`
Test refs: None yet

The shared DTO should be one cross-portal shape, but it should represent surface-resolved metadata and stable actions, not storage delivery internals.

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
- `thumbnail_url` should stay lightweight and optional
- `preview_url` should be used only when a richer preview action exists
- `open_url` remains the current compatibility baseline during rollout

## Surface Endpoint Rule

Status: Proposed target contract
Code refs: `ifitwala_ed/api/org_communication_archive.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/docs/high_concurrency_contract.md`
Test refs: `ifitwala_ed/api/test_org_communication_archive.py`, `ifitwala_ed/api/test_teaching_plans.py`

The correct Ed contract is surface-owned read models, not a generic file-preview API.

Allowed patterns:

- existing aggregate page-init endpoints include `AttachmentPreviewItem[]`
- a dedicated surface attachment endpoint exists only when the surface is independently loaded and remains bounded

Forbidden patterns:

- one request per attachment
- a generic cross-portal `get_file_preview(file_id)` as the main portal contract
- SPA-side permission inference

Examples of acceptable surface owners:

- org communication archive/detail
- student learning space resource shelves
- future task-submission review detail
- future guardian-facing reporting/document surfaces

## Portal Authorization Rule

Status: Proposed target contract
Code refs: `ifitwala_ed/api/file_access.py`, `ifitwala_ed/api/org_comm_utils.py`, `ifitwala_ed/curriculum/materials.py`
Test refs: `ifitwala_ed/api/test_file_access.py`, `ifitwala_ed/api/test_org_communication_archive.py`, `ifitwala_ed/api/test_teaching_plans.py`

Authorization remains surface-specific and server-side:

- staff access follows the owning workflow and operational permissions
- student access is limited to student-visible records and released artifacts
- guardian access is limited to guardian-authorized family/student surfaces with no sibling leakage unless explicitly documented

The frontend is presentation only. It must never widen or infer access.

## Cross-App Implementation Plan

Status: Proposed phased plan
Code refs: `ifitwala_ed/api/file_access.py`, `ifitwala_ed/api/org_communication_archive.py`, `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans.py`
Test refs: None yet for preview-specific rollout

Phase 1: documentation and contract lock

- keep current `open_url` behavior as baseline
- lock the Ed/Drive ownership split in canonical docs in both repos
- forbid portal-direct Drive grant calls for Ed-owned surfaces
- keep Phase 1 media scope narrow: image preview first, optional PDF preview second, no broad media ambitions

Phase 2: Drive dependency foundation

- use the existing Drive image-derivative lifecycle and derivative-role grant resolution as the first foundation
- keep PDF preview and wider media support deferred until the image path is stable

Phase 3: Ed service foundation

- add a shared Ed attachment preview builder service
- add stable preview/open/download routes that re-check surface authorization and then resolve Drive grants
- keep route ownership explicit by surface or shared Ed file-access helpers

Phase 4: shared SPA layer

- add display-only attachment preview components and local interaction composables
- lazy load rich previews; do not dominate routed pages with giant viewers

Phase 5: rollout order

- Org Communication first
- supporting materials and task resources second
- task submissions, feedback, and stricter version-aware evidence surfaces after the foundation is stable

Phase 6: regression protection

- add permission-matrix tests per surface
- add route tests for preview/open/download behaviors
- validate that page-init remains bounded and does not introduce attachment waterfalls

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
