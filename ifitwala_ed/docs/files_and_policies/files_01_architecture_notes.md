# Files And Documents Architecture — Ifitwala_Ed

Status: LOCKED target architecture
Date: 2026-04-19
Code refs:
- `ifitwala_ed/utilities/governed_uploads.py`
- `ifitwala_ed/integrations/drive/bridge.py`
- `ifitwala_ed/api/file_access.py`
Test refs: Pending as part of the boundary refactor

## Bottom line

- `ifitwala_drive` is the sole governance and execution authority for governed files and media.
- `ifitwala_ed` remains the workflow, permission, tenant-scope, and surface-visibility authority.
- `File Classification` is not part of the target architecture and must be removed during the refactor.
- Any temporary compatibility projection into Frappe-native rows is non-authoritative and must be removable.

## 1. Scope

This architecture governs all governed file/media flows in Ifitwala_Ed:

- task materials and task submissions
- admissions documents and profile images
- employee, student, guardian, school, and organization media
- org communication attachments
- future portfolio, journal, and similar governed uploads

It applies across:

- Desk
- SPA
- web/portal flows
- background jobs
- imports and automation

There are no governed-flow exceptions.

## 2. Core decision

Ed no longer owns governed file execution.

Target model:

- Ed decides what a file means in product context.
- Drive decides how the file is uploaded, stored, versioned, derived, previewed, granted, and erased.

Implications:

- no new governed flow may write bytes outside Drive
- no new governed flow may move or rename Drive-managed objects from Ed
- no new governed flow may create derivatives outside Drive
- no new governed flow may treat `File Classification` as authority

## 3. Non-negotiable invariants

### 3.1 One authoritative owner

Every governed file has exactly one authoritative business-document owner.

Owner is never:

- the uploader
- the current user
- the human subject of the file unless that subject document is the owning business record

### 3.2 Slot semantics are mandatory

Every governed file must have one resolved slot.

Slots control:

- replacement behavior
- versioning
- retention
- downstream workflow meaning
- deletion scope

### 3.3 No orphan governed files

Every governed file must resolve:

- owner doctype/name
- attached target when the product surface needs one
- primary subject
- organization
- school when required by the owner workflow
- purpose
- retention policy
- slot

### 3.4 File content is not the business record

Deleting or erasing file content must not break:

- grades
- analytics
- admissions decisions
- structured academic history
- operational records that reference the file

### 3.5 No raw path assumptions

No Ed code or UI surface may:

- guess storage paths
- persist storage paths as product truth
- use `/private/...` paths as the primary browser contract

Only server-owned routes, canonical refs, and Drive-issued grants are valid contracts.

### 3.6 Heavy file work stays off the request path

The request path may do:

- permission checks
- workflow validation
- upload session creation
- blob finalize
- canonical file/version/binding creation
- post-finalize business mutation

The request path may not do:

- synchronous derivative generation
- repeated disk probes for read paths
- storage traversal to discover display URLs
- long loops over governed files

### 3.7 Folder trees are navigation, not governance truth

Folders may support:

- browse UX
- reuse
- search organization

Folders do not determine:

- ownership
- scope
- permissions
- slot meaning
- retention

## 4. Authority split

| Layer | Authority |
| --- | --- |
| `ifitwala_ed` | workflow semantics, tenant scope, permission checks, workflow-specific viewer rules, workflow-specific post-finalize mutation |
| `ifitwala_drive` | upload sessions, blob ingress, storage keys, finalize, canonical refs, versions, bindings, derivatives, grants, audit, erasure execution |
| Transitional compatibility only | Frappe-native `File` rows or other projections still needed during migration |

Important:

- transitional compatibility rows are not governance truth
- new features must not be designed around transitional rows

## 5. Canonical governed-file model

### 5.1 `Drive Upload Session`

Drive owns upload session lifecycle and stores the resolved contract needed for finalize.

At minimum the session persists:

- `workflow_id`
- `contract_version`
- resolved owner doctype/name
- resolved attached doctype/name/field when applicable
- resolved subject data
- resolved governance data: purpose, retention, slot, organization, school
- upload strategy and temporary object key
- expected size, filename, MIME hint, status

### 5.2 `Drive File`

The governed file identity.

It owns:

- canonical ref
- owner
- slot
- organization/school scope
- current version pointer
- active lifecycle state

### 5.3 `Drive File Version`

Immutable blob version rows.

Drive versioning is per governed file/slot, not per raw `File` row.

### 5.4 `Drive Binding`

The surface-facing binding between a governed file and a business surface or surface row.

Bindings exist for product reuse and retrieval.
They are not a second governance system.

### 5.5 `Drive File Derivative`

The only derivative/preview authority.

Profile-image sizes, thumbnails, viewer previews, and similar artifacts belong here.

### 5.6 Transitional compatibility rows

If a Frappe-native projection is still temporarily required during migration:

- it is derived from Drive metadata
- it must not own storage movement
- it must not own derivative generation
- it must not own governance decisions

`File Classification` is explicitly outside the target model and must be removed.

## 6. Canonical upload execution model

1. Ed resolves the governed workflow context and authorizes the actor.
2. Drive creates the upload session from the authoritative workflow spec.
3. The browser uploads bytes to the Drive-issued target.
4. For local/proxy mode only, bytes go through Drive `upload_session_blob`.
5. Drive finalizes the upload:
   - validates session state
   - validates bytes and MIME
   - finalizes the object into governed storage
   - creates `Drive File`, `Drive File Version`, and `Drive Binding`
6. Drive triggers the workflow-specific post-finalize mutation in Ed.
7. Drive enqueues derivatives, previews, scans, and other heavy follow-up work asynchronously.

Forbidden patterns:

- Ed writing temporary objects into Drive storage
- Ed mutating `Drive Upload Session` directly
- Drive importing Ed dispatcher/file-routing internals to finish the create path

## 7. Canonical read and display model

For private governed files:

1. Ed authorizes the surface-specific read/open action.
2. Drive resolves the correct artifact for download or preview.
3. The browser receives a short-lived grant or a server-owned route response.

Rules:

- no raw `/private/...` path as the primary product contract
- no synchronous disk probing in list surfaces
- no per-surface reinvention of derivative selection

## 8. Storage model

Drive owns:

- storage backend choice
- storage object key
- temporary object handling
- final object placement

Ed must not:

- rename Drive-managed storage objects
- move Drive-managed blobs into Ed folder trees
- rewrite object identity after finalize

Folder hints and browse organization are allowed only as Drive-owned read models.

## 9. Derivatives and media variants

Only Drive generates and stores governed derivatives.

That includes:

- profile image variants
- thumbnails
- viewer previews
- future PDF/image preview artifacts

Ed must not create governed sibling `File` rows for derivatives.

## 10. End-state rule for `File Classification`

`File Classification` was part of the earlier Ed-local governance model.

It is not part of the target architecture.

Phase target:

- stop treating it as authority
- stop adding new behavior that depends on it
- migrate existing governed semantics into Drive-owned metadata
- remove the DocType and patch existing records as part of the refactor

## 11. Current runtime note

Current code does not fully conform to this document.

The current-runtime leaks and remediation order are documented in:

- `ifitwala_ed/docs/files_and_policies/files_03_implementation.md`
