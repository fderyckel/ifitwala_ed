# Governed Files Implementation Status And Remediation Order

Status: Current runtime and gap register
Date: 2026-04-20
Code refs:
- `ifitwala_ed/utilities/governed_uploads.py`
- `ifitwala_ed/utilities/file_management.py`
- `ifitwala_ed/utilities/image_utils.py`
- `ifitwala_ed/integrations/drive/authority.py`
- `ifitwala_ed/integrations/drive/content_uploads.py`
- `ifitwala_ed/integrations/drive/tasks.py`
- `ifitwala_ed/integrations/drive/bridge.py`
- `ifitwala_ed/integrations/drive/workflow_specs.py`
- `ifitwala_ed/api/task_submission.py`
- `ifitwala_ed/assessment/task_submission_service.py`
- `ifitwala_drive/api/uploads.py`
- `ifitwala_drive/services/uploads/finalize.py`
Test refs:
- `ifitwala_drive/tests/test_task_submission_upload_flow.py`
- `ifitwala_drive/tests/test_media_and_admissions_wrappers.py`
- `ifitwala_drive/tests/test_preview_jobs.py`
- `ifitwala_ed/utilities/test_image_utils_unit.py`
- `ifitwala_ed/utilities/test_governed_uploads_task_flows.py`
- `ifitwala_ed/admission/test_admissions_portal_uploads_unit.py`
- `ifitwala_ed/api/test_task_submission_unit.py`
- `ifitwala_ed/assessment/test_task_submission_service.py`
- `ifitwala_ed/integrations/drive/test_tasks.py`

## Bottom line

- The locked architecture is Drive-owned governed execution with Ed-owned workflow semantics.
- Ingress and finalize now conform to that boundary.
- Authority collapse is now implemented in runtime code.
- `File Classification` is no longer a live runtime authority or projection path.
- This file documents the remaining non-conforming behavior so agents stop copying it into new work.
- New work must follow `files_01_architecture_notes.md`, not the accidental patterns listed here.

## 1. What is true today

Today the system already has substantial Drive-based infrastructure:

- Drive upload sessions
- temporary object handling
- storage abstraction
- finalize logic
- Drive file/version/binding models
- preview/derivative infrastructure
- grant issuance

The main boundary leaks at ingress and finalize are now sealed.
Remaining work is now about tightening workflow-spec contracts and expanding Drive-native reuse/browse flows without reopening the boundary.

## 2. Boundary status and remaining non-conforming behaviors

### 2.1 Resolved: Ed no longer writes temporary objects into Drive storage

Current code:

- `ifitwala_ed/utilities/governed_uploads.py::_drive_upload_and_finalize`
- `ifitwala_drive/api/uploads.py::ingest_upload_session_content`

Current behavior:

- Ed creates the Drive session
- Ed hands buffered upload bytes to a Drive-owned ingest helper
- Drive owns storage writes and `Drive Upload Session` state mutation

Outcome:

- Phase 2 is complete in code
- new work must continue using the Drive ingress seam

### 2.2 Resolved: Drive finalize no longer imports Ed dispatcher internals

Current code:

- `ifitwala_drive/services/uploads/finalize.py`
- `ifitwala_drive/services/files/projections.py`
- `ifitwala_ed/hooks.py`
- `ifitwala_ed/utilities/image_utils.py`

Current behavior:

- Drive finalization creates the native `File` compatibility projection itself
- Drive no longer creates `File Classification` rows
- Ed `File` hooks now point directly at `image_utils` and no longer route or rename governed files

Why this is acceptable only as a transition:

- Drive now owns the finalize execution boundary
- the native `File` projection still exists only to keep current surfaces running until later cleanup

Rules:

- do not reintroduce Drive -> Ed dispatcher/file-routing imports
- do not treat compatibility projections as governance authority

### 2.3 Resolved: Ed no longer remaps finalized Drive storage

Current behavior:

- governed finalize leaves storage identity under Drive-owned object keys
- Ed no longer routes or renames governed files after finalize
- `file_management.py` now retains only the governed-upload gate and task-submission folder helper

Outcome:

- Phase 4 removed the last live Ed-side file-routing path for governed uploads
- Drive object keys remain authoritative after finalize

### 2.4 Governance truth is duplicated

Current duplicated authorities include:

- `Drive Upload Session.intended_*`
- `Drive File`
- native `File` compatibility rows for migration and legacy storage references only

Why this is wrong:

- it invites drift
- it multiplies migration cost
- it encourages per-surface logic to choose the wrong source of truth

Target fix:

- Drive metadata becomes sole governance authority
- current governed DTO surfaces such as admissions documents, staff admissions review, org communication, planning, learning, and task evidence must resolve `open_url` / `preview_url` / `thumbnail_url` from Drive identity, not by rediscovering `File.file_url`
- staff Morning Brief attachment previews and employee birthday images follow the same rule: org-communication previews resolve by governed attachment slot, and Employee image reads must survive compatibility `File` rotation by resolving the current governed profile-image authority first
- historical `File Classification` rows are removed by migration patch once every row has matching Drive authority
- the retired `File Classification` DocTypes are then removed by an explicit schema-retirement patch

### 2.5 Derivatives exist in two systems

Previous drift:

- `ifitwala_ed/utilities/image_utils.py`
- `ifitwala_drive/services/files/derivatives.py`

Corrected behavior:

- Drive is now the only derivative authority
- Ed no longer creates governed sibling `File` rows for profile-image variants
- Ed still exposes compatibility variant keys such as `profile_image_thumb`, `profile_image_card`, and `profile_image_medium`, but those keys now resolve to derivative roles on the current `profile_image` Drive file:
  - `profile_image_thumb` -> `thumb`
  - `profile_image_card` -> `card`
  - `profile_image_medium` -> `viewer_preview`

Why the old model was wrong:

- duplicate derivative logic
- duplicate storage concerns
- request-path heaviness

Implemented fix:

- Drive is the only derivative authority
- Ed synchronous derivative generation is removed
- profile-image derivative scheduling now goes through the Drive preview pipeline

### 2.6 Resolved: governed profile-image reads no longer probe storage directly

Current code:

- `ifitwala_ed/utilities/image_utils.py`

Current behavior:

- profile-image compatibility keys still exist for Ed surfaces
- those keys now resolve from current `Drive File` metadata, `Drive File Derivative` readiness, and file-access grant routes
- governed original-image fallback uses the current Drive-owned file rather than disk accessibility probing

Why the old model was wrong:

- hot paths become DB + disk heavy
- read behavior depends on storage inspection instead of canonical metadata/grants

Implemented fix:

- read/open/display decisions come from Drive metadata and grants
- Ed list surfaces stop probing disk for governed profile-image delivery

### 2.7 Resolved: governed delivery routes no longer emit raw private redirects

Current code:

- `ifitwala_ed/api/file_access.py`

Current behavior:

- governed private-media routes now either:
  - explicit external URLs allowed by the surface contract
  - explicit public `/files/...` URLs allowed by the surface contract
  - just-in-time safe Drive grant targets
  - inline streamed content when the resolved Drive/local grant target is an in-site private path
- governed private-media routes must never emit raw `/private/...` redirect targets back to the browser
- Ed no longer probes local disk to rediscover file reality before choosing a governed delivery path for admissions, academic, guardian, employee, org-communication, or public-website media routes

Why the old model was wrong:

- it reintroduced storage probing into hot read paths
- it treated local disk as a second delivery authority
- it kept route behavior dependent on storage layout rather than Drive metadata and grant policy

Implemented fix:

- governed delivery routes now resolve only from safe public/external targets or Drive grants
- when a local-storage Drive grant resolves to an in-site private path, Ed serves it inline instead of redirecting the browser to a raw `/private/...` URL

### 2.8 Workflow semantics are too stringly-typed

Current code:

- `ifitwala_ed/integrations/drive/bridge.py`
- `ifitwala_ed/integrations/drive/workflow_specs.py`
- Drive wrapper services under `ifitwala_drive/services/integration/`

Previous drift:

- many upload flows hand-author payload dicts
- purpose/slot/binding semantics are duplicated across code and docs

Implemented fix:

- Ed now exposes one runtime `GovernedUploadSpec` registry in `workflow_specs.py`
- Drive wrapper services now stamp `workflow_id`, `contract_version`, and `workflow_payload`
- `Drive Upload Session.upload_contract_json` now persists workflow metadata under `workflow`
- finalize and post-finalize dispatch now resolve by persisted `workflow_id` first and fall back to detection only for pre-registry sessions

Remaining cleanup:

- some wrapper-specific service modules still exist for public ergonomics
- a few historical finalize sessions may still rely on workflow detection fallback instead of persisted workflow metadata
- some historical audit/discussion notes may still mention the retired `File Classification` and Ed-side derivative model and must not be treated as runtime design guidance

### 2.9 Resolved: student task submission uploads now follow the governed append-only path

Current code:

- `ifitwala_ed/api/task_submission.py`
- `ifitwala_ed/assessment/task_submission_service.py`
- `ifitwala_ed/integrations/drive/tasks.py`
- `ifitwala_ed/integrations/drive/content_uploads.py`

Previous drift:

- student portal uploads depended on generic `Task Submission.write` checks even though Student ACLs do not grant that permission
- the student submission service tried to finalize governed files before the new `Task Submission` owner row existed

Implemented fix:

- student text, link, and file evidence now all go through the same `create_or_resubmit` business endpoint
- when files are present, Ed inserts the new append-only `Task Submission` row first, then finalizes governed files against that persisted owner, then saves attachment rows on that version
- the `task.submission` workflow now preserves staff write checks but also allows the current student when the session student matches `Task Submission.student`
- the fix does not broaden Student DocType metadata permissions, and portal clients still do not call Drive APIs directly

## 3. Rules for new work during remaining cleanup

Until the remaining cleanup lands:

- do not add new direct writes to Drive storage from Ed
- do not add new `File Classification`-based workflow logic
- do not add new Ed-side derivative generation
- do not add new routing/rename logic for Drive-managed objects
- do not add new anonymous upload payloads that omit `workflow_id`
- do not return raw storage-shaped `/private/...` values to SPA/API consumers when a server-owned open/preview URL is required by the surface contract
- do not reintroduce reload fallback wrappers, `sys.path` import rescue, or hidden cross-app service imports

## 4. Remediation order

### Phase 1

Docs reset.

Purpose:

- lock the target boundary
- stop agents from reproducing the old model

### Phase 2

Seal ingress.

Required outcomes:

- completed in code

### Phase 3

Seal finalize.

Required outcomes:

- completed in code

### Phase 4

Collapse authority.

Required outcomes:

- Drive metadata becomes sole governance authority
- completed in code
- cleanup patch `ifitwala_ed.patches.backfill_drive_authority_for_classified_files` materializes authoritative Drive rows for historical governed files before deletion
- cleanup patch `ifitwala_ed.patches.remove_file_classification_rows` removes historical rows only after matching `Drive File` coverage exists

### Phase 5

Clean read and derivative paths.

Required outcomes:

- Drive becomes sole derivative authority
- Ed read paths stop probing storage directly
- completed in code for governed profile-image surfaces and Drive-backed derivative routing

### Phase 6

Runtime workflow spec registry.

Required outcomes:

- completed in code
- Ed owns one versioned `GovernedUploadSpec` registry in `ifitwala_ed/integrations/drive/workflow_specs.py`
- Drive persists `workflow_id` and `contract_version` with the session upload contract
- finalize and post-finalize dispatch resolve by persisted workflow metadata rather than branch cascades
- wrapper services now create sessions through `workflow_id` plus workflow-specific identifiers internally, while preserving the current public wrapper endpoints

### Phase 7

Governed delivery cleanup.

Required outcomes:

- completed in code
- governed read/open routes resolve only to safe public/external targets or Drive grants
- raw private redirect targets are never emitted to the browser; local in-site private grant targets are served inline

### Phase 8

Runtime wrapper cleanup.

Required outcomes:

- completed in code
- Ed same-repo integration entrypoints now use explicit imports instead of same-repo dynamic imports
- Ed no longer uses reload fallback wrappers or hidden Drive service fallbacks to recover missing public API methods
- Drive no longer uses `sys.path` rescue to reach Ed bridge modules and now resolves only explicit public bridge modules

## 5. Relationship to the canonical architecture

Use this file to understand what still needs to be fixed.

Do not use it to justify keeping the current leaks.

Canonical target:

- `ifitwala_ed/docs/files_and_policies/files_01_architecture_notes.md`
- `ifitwala_ed/docs/files_and_policies/files_07_education_file_semantics_and_cross_app_contract.md`
