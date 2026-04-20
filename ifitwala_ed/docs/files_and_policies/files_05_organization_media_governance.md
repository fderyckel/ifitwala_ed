# Organization Media Governance — Canonical Contract

This note defines the live governed-file contract for reusable public-facing organization and school media.

It reflects the post-refactor model:

- `ifitwala_drive` is the governed file authority
- `ifitwala_ed` owns workflow meaning, organization/school scope, and UI wiring
- `Drive File` is the authoritative metadata row
- `File Classification` and the Ed dispatcher are retired and must not be reintroduced

---

## 1. Scope

**Status:** Active
**Code refs:** `ifitwala_ed/utilities/governed_uploads.py`, `ifitwala_ed/utilities/organization_media.py`, `ifitwala_ed/utilities/governed_file_contract.py`, `ifitwala_ed/setup/doctype/organization/organization.py`, `ifitwala_ed/school_settings/doctype/school/school.py`, `ifitwala_drive/services/integration/ifitwala_ed_media.py`
**Test refs:** `ifitwala_ed/utilities/test_organization_media.py`

This contract governs reusable public-facing media used for:

- organization branding
- school branding
- reusable website/gallery imagery
- school and organization landing surfaces
- marketing/admissions public media

It does not change student, guardian, employee, applicant, or assessment file rules.

---

## 2. Ownership Model

### 2.1 Root owner

The authoritative governed owner is the `Organization`.

Why:

- every `School` belongs to an `Organization`
- shared branding belongs to the organization scope by default
- organization-root ownership keeps reuse and inheritance predictable across nested organizations

### 2.2 School specificity

School-scoped media stays inside the same governed model.

Rules:

- `organization` is always required
- `school` is optional
- when `school` is present, the file remains organization-owned but school-scoped
- school scope is metadata on the governed Drive file, not a second governance system

### 2.3 Authoritative metadata

The live authority row is `Drive File`.

Required organization-media semantics:

- `primary_subject_type = Organization`
- `primary_subject_id = <organization>`
- `data_class = operational`
- `purpose = organization_public_media`
- `retention_policy = immediate_on_request`

---

## 3. Slot Contract

Implemented slot patterns:

- `organization_logo__<organization>`
- `school_logo__<school>`
- `school_gallery_image__<gallery_row_name>`
- `organization_media__<media_key>`

Rules:

- slot meaning is resolved server-side
- callers must not invent path-like storage identity from the slot
- UI code may store the returned `file`, `file_url`, and surface-specific reference fields, but not storage keys

---

## 4. Upload Boundary

### 4.1 Required path

Organization media uploads must flow through:

1. `ifitwala_ed.utilities.governed_uploads.*`
2. `ifitwala_drive.api.media.*`
3. Drive upload session creation
4. Drive-owned ingest
5. Drive-owned finalize
6. native `File` projection plus authoritative `Drive File`

### 4.2 Forbidden path

Do not:

- call `File.insert()` directly from organization-media workflow code
- route files through the retired Ed dispatcher
- recreate organization-media governance in Ed-local tables
- guess storage paths or private URLs in the UI

---

## 5. Visibility & Inheritance

Server-side visibility must follow nested organization and school scope.

Allowed sources for a school:

1. school-scoped media on the current school
2. school-scoped media on ancestor schools in the same organization tree
3. organization-scoped media on the current organization
4. organization-scoped media on ancestor organizations

Forbidden sources:

- sibling organizations
- cousin organizations
- sibling school branches
- unrelated school nodes inside the same organization tree

This scope math belongs in shared server helpers, not the browser.

---

## 6. Persisted Surface Fields

Current Desk/runtime surfaces persist:

- `Organization.organization_logo_file` -> governed `File`
- `Organization.organization_logo` -> canonical returned file URL
- `School.school_logo_file` -> governed `File`
- `School.school_logo` -> canonical returned file URL
- `Gallery Image.governed_file` -> governed `File`
- `Gallery Image.school_image` -> canonical returned file URL

Legacy URL-only values are non-canonical and must be rejected on save.

---

## 7. Reuse Workflow

Desk image pickers for organization/school media must be reuse-first:

- first offer existing governed media in visible scope
- if no suitable file exists, offer upload into governed organization media
- do not leave the user at a dead end with an empty picker and no next step

Implemented now:

- school and organization forms enforce governed media references
- list/browse helpers resolve visible organization media from `Drive File`
- upload wrappers return server-owned file references instead of storage guesses

---

## 8. Read Contract

Organization-media readers must resolve from:

- `Drive File` for authority and scope
- native `File` for returned `file_url`, `file_name`, and privacy flags

They must not:

- query `File Classification`
- depend on retired derivative sibling files
- infer visibility from folder names

---

## 9. Non-Negotiable Rules

- `File Classification` is retired for organization media
- the Ed dispatcher is retired for organization media
- Drive owns ingest, finalize, and authoritative metadata
- Ed owns scope validation, slot resolution, and surface wiring
- no new code may recreate organization-media governance outside Drive
