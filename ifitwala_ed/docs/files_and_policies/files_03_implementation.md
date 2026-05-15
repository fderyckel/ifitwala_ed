# Governed Files Implementation Status And Remediation Order

Status: Current runtime and gap register
Date: 2026-04-25
Code refs:
- `ifitwala_ed/utilities/governed_uploads.py`
- `ifitwala_ed/utilities/file_management.py`
- `ifitwala_ed/utilities/image_utils.py`
- `ifitwala_ed/api/file_access.py`
- `ifitwala_ed/integrations/drive/authority.py`
- `ifitwala_ed/integrations/drive/content_uploads.py`
- `ifitwala_ed/integrations/drive/media.py`
- `ifitwala_ed/integrations/drive/tasks.py`
- `ifitwala_ed/integrations/drive/bridge.py`
- `ifitwala_ed/integrations/drive/workflow_specs.py`
- `ifitwala_ed/api/task_submission.py`
- `ifitwala_ed/assessment/task_submission_service.py`
- `ifitwala_drive/api/media.py`
- `ifitwala_drive/services/integration/ifitwala_ed_media.py`
- `ifitwala_drive/api/uploads.py`
- `ifitwala_drive/services/uploads/finalize.py`
Test refs:
- `ifitwala_ed/api/test_file_access.py`
- `ifitwala_ed/api/test_file_access_unit.py`
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
- the trusted buffered-ingest seam resolves the session from Drive authority and does not require Ed to replay browser upload-token headers

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
- Ed still exposes compatibility variant keys such as `profile_image_thumb`, `profile_image_card`, and `profile_image_medium`, but those keys are semantic display variants resolved by Drive on the current `profile_image` file. Ed docs and SPA contracts must not name Drive's internal derivative roles.
- compact identity/avatar surfaces should request the compact profile-image variant only and should not silently substitute larger preview variants

Why the old model was wrong:

- duplicate derivative logic
- duplicate storage concerns
- request-path heaviness

Implemented fix:

- Drive is the only derivative authority
- Ed synchronous derivative generation is removed
- profile-image derivative scheduling now goes through the Drive preview pipeline
- when Ed roster/avatar surfaces detect missing current-version profile-image derivatives, they request Drive regeneration through the explicit media wrapper seam rather than importing Drive derivative services directly
- the legacy profile-image recovery path is patch-driven, not a permanent runtime fallback; the repair patches walk Employee, Student, Guardian, and admissions applicant/guardian profile-image rows, rebuild or resync missing governed profile images through the public Drive upload seam, and materialize refreshed compact/card/richer preview variants for current governed profile images during migrate so avatar surfaces stop falling back to originals after legacy repair; Student rows are normalized through `ifitwala_ed.patches.backfill_student_profile_images`
- Ed profile-image and public-website media reads now depend on public Drive API wrappers only; they do not import Drive integration services directly and they do not fall back to generic Drive owner-doc grant APIs for those Ed-owned surfaces
- small roster/avatar surfaces such as gradebook, attendance, and student-log lookup now consume governed profile-image derivatives only and do not fall back to original-file URLs when no derivative is ready
- guardian portal-chrome avatars and student portal identity now consume governed profile-image derivatives only and never fall back to the original file on those compact identity surfaces
- public website people surfaces now resolve approved employee profile-image derivatives through a guest-safe public employee-image route; they do not use the authenticated employee file route and they do not fall back to the original full-size image

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
- guest-visible public website media now resolves through a surface-scoped Drive media wrapper, so public landing-page reads do not depend on raw `Organization` DocType read permission
- guest-visible public employee photos now follow the same pattern through a dedicated public employee-image wrapper and route, so public website staff photos no longer depend on the authenticated employee read path

Why the old model was wrong:

- it reintroduced storage probing into hot read paths
- it treated local disk as a second delivery authority
- it kept route behavior dependent on storage layout rather than Drive metadata and grant policy
- it left public website media on the generic Drive access path even though Ed already owns the public-brand visibility decision for that surface

Implemented fix:

- governed delivery routes now resolve only from safe public/external targets or Drive grants
- when a local-storage Drive grant resolves to an in-site private path, Ed serves it inline instead of redirecting the browser to a raw `/private/...` URL
- public website media now uses the same surface-scoped wrapper pattern as other Ed-owned grant surfaces when generic owner-doc checks are narrower than the actual surface contract

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
- new session creation fails closed without `workflow_id`
- the locked session/finalize DTOs now expose `workflow_id`, `contract_version`, and typed `workflow_result`
- wrapper-specific extras such as `row_name`, admissions item metadata, or gallery captions must live under `workflow_result`, not as scattered top-level session/finalize keys
- Drive finalize checks persisted workflow metadata before invoking the Ed finalize bridge, so legacy-invalid sessions fail in Drive before storage resolution or business-record revalidation
- finalize and post-finalize dispatch now resolve only by persisted `workflow_id`
- sessions without persisted workflow metadata are legacy-invalid at finalize time; migration/backfill must materialize explicit workflow metadata through a patch or retire the session
- task files now use `supporting_material.file`; legacy Task attachment rows are migrated once into `Supporting Material` plus `Material Placement` and are no longer a runtime upload surface

Remaining cleanup:

- some wrapper-specific service modules still exist for public ergonomics
- some historical audit/discussion notes may still mention the retired `File Classification` and Ed-side derivative model and must not be treated as runtime design guidance
- some compatibility-heavy write helpers still fetch the native `File` projection after finalize, so `file_id` remains part of the locked generic finalize DTO until those reads are fully retired

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
- implemented for governed DTO/open/preview/erasure decisions; not complete for native `File` projection retirement
- cleanup patch `ifitwala_ed.patches.backfill_drive_authority_for_classified_files` materializes authoritative Drive rows for historical governed files before deletion
- cleanup patch `ifitwala_ed.patches.remove_file_classification_rows` removes historical rows only after matching `Drive File` coverage exists
- remaining native `File` projection removal requires an explicit schema/workflow retirement phase because current Drive DocTypes and some Ed post-upload writes still carry `file_id`

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
- Drive persists the spec-owned `is_private` value with the session upload contract; UI callers and wrapper services are not a second privacy authority
- Drive validates that persisted workflow metadata exists before invoking Ed finalize delegates
- finalize and post-finalize dispatch resolve by persisted workflow metadata rather than branch cascades or workflow detection
- finalize-time workflow detection fallback for pre-registry sessions is retired; legacy session repair belongs in explicit migration/backfill patches only
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
