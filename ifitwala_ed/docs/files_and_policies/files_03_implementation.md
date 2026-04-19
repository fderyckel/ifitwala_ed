# Governed Files Implementation Status And Remediation Order

Status: Current runtime and gap register
Date: 2026-04-19
Code refs:
- `ifitwala_ed/utilities/governed_uploads.py`
- `ifitwala_ed/utilities/file_dispatcher.py`
- `ifitwala_ed/utilities/file_management.py`
- `ifitwala_ed/utilities/image_utils.py`
- `ifitwala_ed/integrations/drive/bridge.py`
- `ifitwala_drive/api/uploads.py`
- `ifitwala_drive/services/uploads/finalize.py`
Test refs:
- `ifitwala_drive/tests/test_task_submission_upload_flow.py`
- `ifitwala_ed/utilities/test_governed_uploads_task_flows.py`
- `ifitwala_ed/utilities/test_file_dispatcher_hooks.py`

## Bottom line

- The locked architecture is Drive-owned governed execution with Ed-owned workflow semantics.
- Ingress and finalize now conform to that boundary.
- Current runtime still has remaining migration gaps after finalize.
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
The remaining problems are compatibility baggage and read/derivative cleanup.

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
- `ifitwala_ed/utilities/file_dispatcher.py`

Current behavior:

- Drive finalization creates the native `File` compatibility projection itself
- Drive may still create a temporary `File Classification` projection from authoritative upload-session metadata
- Ed legacy `File` hooks explicitly skip routing and derivative side effects for Drive compatibility rows

Why this is acceptable only as a transition:

- Drive now owns the finalize execution boundary
- compatibility projections still exist only to keep current surfaces running until Phase 4

Rules:

- do not reintroduce Drive -> Ed dispatcher/file-routing imports
- do not treat compatibility projections as governance authority

### 2.3 Ed can physically remap Drive-managed storage after finalize

Current code:

- `ifitwala_ed/utilities/file_management.py::route_uploaded_file`
- `ifitwala_drive/services/storage/local.py::finalize_temporary_object`

Observed behavior:

- Drive local storage finalizes to a Drive-owned object key under `/private/files/ifitwala_drive/...`
- Ed routing logic can then rename/move the file into an Ed folder path and rewrite `File.file_url`

Why this is wrong:

- storage object identity belongs to Drive
- Ed-side moves can desynchronize object keys from actual blob location

Target fix:

- Ed never renames or routes Drive-managed storage objects
- Drive object keys remain authoritative after finalize

### 2.4 Governance truth is duplicated

Current duplicated authorities include:

- `Drive Upload Session.intended_*`
- `File Classification`
- `Drive File`
- in some places `File` custom fields

Why this is wrong:

- it invites drift
- it multiplies migration cost
- it encourages per-surface logic to choose the wrong source of truth

Target fix:

- Drive metadata becomes sole governance authority
- `File Classification` is removed

### 2.5 Derivatives exist in two systems

Current code:

- `ifitwala_ed/utilities/image_utils.py`
- `ifitwala_drive/services/files/derivatives.py`

Observed behavior:

- Ed generates governed profile-image variants synchronously
- Drive also has a derivative system and async preview pipeline

Why this is wrong:

- duplicate derivative logic
- duplicate storage concerns
- request-path heaviness

Target fix:

- Drive becomes the only derivative authority
- Ed synchronous derivative generation is removed

### 2.6 Read paths still probe storage directly

Current code:

- `ifitwala_ed/utilities/image_utils.py`

Observed behavior:

- read helpers perform repeated file accessibility checks
- some helpers still inspect disk existence or storage-backed file accessibility

Why this is wrong:

- hot paths become DB + disk heavy
- read behavior depends on storage inspection instead of canonical metadata/grants

Target fix:

- read/open/display decisions come from Drive metadata and grants
- Ed list surfaces stop probing disk

### 2.7 Workflow semantics are too stringly-typed

Current code:

- `ifitwala_ed/integrations/drive/bridge.py`
- workflow-specific upload builders across Ed

Observed behavior:

- many upload flows hand-author payload dicts
- purpose/slot/binding semantics are duplicated across code and docs

Why this is wrong:

- browser-time failure becomes the first real integration test
- semantic drift is easy

Target fix:

- one versioned `GovernedUploadSpec` per workflow

## 3. Rules for new work before the code refactor lands

Until the implementation is cleaned up:

- do not add new direct writes to Drive storage from Ed
- do not add new `File Classification`-based workflow logic
- do not add new Ed-side derivative generation
- do not add new routing/rename logic for Drive-managed objects
- do not expand the dynamic-import wrapper surface unless strictly necessary to keep the app running during migration

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
- `File Classification` is migrated off and removed

### Phase 5

Clean read and derivative paths.

Required outcomes:

- Drive becomes sole derivative authority
- Ed read paths stop probing storage directly

## 5. Relationship to the canonical architecture

Use this file to understand what still needs to be fixed.

Do not use it to justify keeping the current leaks.

Canonical target:

- `ifitwala_ed/docs/files_and_policies/files_01_architecture_notes.md`
- `ifitwala_ed/docs/files_and_policies/files_07_education_file_semantics_and_cross_app_contract.md`
