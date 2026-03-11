# Organization Media Governance — Canonical Contract

This document defines the canonical ownership and governance model for reusable public-facing media used by organizations and schools.

It exists to close the current gap between:

* the global file dispatcher / classification policy, and
* school website / gallery image workflows that still behave like direct attachments.

This contract is forward-looking and intentionally future-proofs the platform for separated application, database, and object-storage deployments.

---

## 1. Scope

**Status:** Partial
**Code refs:** `ifitwala_ed/utilities/file_dispatcher.py`, `ifitwala_ed/utilities/governed_uploads.py`, `ifitwala_ed/utilities/organization_media.py`, `ifitwala_ed/school_settings/doctype/school/school.json`, `ifitwala_ed/school_settings/doctype/school/school.py`, `ifitwala_ed/school_site/doctype/gallery_image/gallery_image.json`
**Test refs:** `ifitwala_ed/utilities/test_organization_media.py`

This contract governs all organization-owned reusable media intended for:

* website / public-site branding
* website blocks (hero, section carousel, leadership, cards)
* organization and school landing surfaces
* shared marketing / admissions imagery

This contract does **not** change student, applicant, employee, or task file rules.

It defines the canonical ownership model for media that can be reused across more than one page or school.

---

## 2. Canonical Ownership Model

**Status:** Partial
**Code refs:** `ifitwala_ed/setup/doctype/file_classification/file_classification.json`, `ifitwala_ed/setup/doctype/file_classification/file_classification.py`, `ifitwala_ed/utilities/file_classification_contract.py`, `ifitwala_ed/utilities/organization_media.py`, `ifitwala_ed/school_settings/doctype/school/school.json`
**Test refs:** `ifitwala_ed/utilities/test_organization_media.py`

### 2.1 Root owner

The canonical owner for reusable public-facing media is **Organization**.

This is the starting point for governance because:

* every School belongs to an Organization
* shared branding normally belongs to the organization, not a single page
* organization ownership avoids duplicate uploads across sibling schools
* nested organizations can inherit and reuse assets predictably

### 2.2 School specificity

School-specific media remains governed under the same organization-owned model.

Rules:

* `organization` is always required
* `school` is optional, but when set it indicates a school-scoped asset under that organization
* school-scoped media is not a separate governance system

### 2.3 Business-document anchoring

For organization media, the governing business document is the owning `Organization`.

When a school-specific asset is uploaded, the file may additionally carry:

* `school` classification field = target school
* optional secondary relation or attachment to school-specific gallery rows

The primary governance owner remains organization-scoped.

---

## 3. Nested Visibility & Inheritance

**Status:** Partial
**Code refs:** `ifitwala_ed/setup/doctype/organization/organization.py`, `ifitwala_ed/governance/policy_scope_utils.py`, `ifitwala_ed/utilities/organization_media.py`, `ifitwala_ed/school_settings/doctype/school/school.py`
**Test refs:** `ifitwala_ed/utilities/test_organization_media.py`

Organization media must respect the NestedSet hierarchy.

### 3.1 Allowed visibility

Given a school attached to organization `O`, selectable media may come from:

* `O`
* any ancestor of `O`
* when media is school-scoped, only the current school or one of its ancestor schools inside `O`

### 3.2 Forbidden visibility

Selectable media must **not** come from:

* sibling organizations
* cousin organizations
* descendant organizations of a sibling
* unrelated trees
* sibling schools inside the same organization
* unrelated school branches inside the same organization

### 3.3 Directionality

Inheritance is one-way:

* ancestor -> descendant is allowed
* descendant -> ancestor is forbidden by default

### 3.4 Precedence

Where defaults or reusable selections are resolved:

1. school-scoped media on the current school
2. school-scoped media on ancestor schools in the current organization
3. organization-owned media on the current organization
4. organization-owned media inherited from nearest ancestor upward

This precedence must be implemented by shared server helpers, not by client-side scope math.

---

## 4. Media Selection Workflow

**Status:** Planned
**Code refs:** `ifitwala_ed/public/js/website_props_builder.js`, `ifitwala_ed/website/block_registry.py`, `ifitwala_ed/website/providers/*.py`
**Test refs:** None

For every school/organization image picker in Desk:

* the primary action is `Choose from Organization Media`
* the secondary action is `Upload to Organization Media`
* free-form file URL typing is not the primary workflow

### 4.1 Reuse-first rule

Editors should first reuse an existing governed asset from the resolved organization scope.

### 4.2 Upload rule

If the needed image does not exist:

* upload must go through a governed upload endpoint
* upload must classify the file immediately
* the resulting asset becomes selectable in the same media picker flow

### 4.3 No dead ends

If the picker finds no matching assets, the UI must still provide a next action:

* upload a new governed image
* or navigate directly to the owning organization media management surface

---

## 5. File Governance Contract

**Status:** Partial
**Code refs:** `ifitwala_ed/utilities/file_dispatcher.py`, `ifitwala_ed/utilities/governed_uploads.py`, `ifitwala_ed/utilities/organization_media.py`, `ifitwala_ed/utilities/file_classification_contract.py`, `ifitwala_ed/setup/doctype/file_classification/file_classification.json`, `ifitwala_ed/school_settings/doctype/school/school.py`, `ifitwala_ed/school_settings/doctype/school/school.js`
**Test refs:** `ifitwala_ed/utilities/test_organization_media.py`

Organization media must follow the same dispatcher-only governance rules as all other governed files.

### 5.1 Required entrypoint

All uploads must go through:

* `create_and_classify_file(...)`
* or a governed wrapper that delegates to it

Direct `File.insert()` remains forbidden.

### 5.2 Required classification extension

Current implementation:

* `File Classification.primary_subject_type` includes `Organization`
* `purpose` includes `organization_public_media`
* `school` is optional for `Organization`-owned classifications
* school logo uploads and school gallery uploads use dispatcher-classified `Organization` media records

### 5.3 Required classification semantics

Implemented values:

* primary subject type: `Organization`
* data class: `operational`
* purpose: `organization_public_media`
* retention policy: `immediate_on_request`
* slot patterns:
  * `school_logo__<school>`
  * `school_gallery_image__<gallery_row_name>`
  * `organization_media__<media_key>`

School surfaces currently use the following persisted references:

* `School.school_logo_file` stores the governed `File`
* `School.school_logo` stores the canonical returned file URL
* `Gallery Image.governed_file` stores the governed `File`
* `Gallery Image.school_image` stores the canonical returned file URL

Legacy rows that still hold only a URL are tolerated temporarily, but new uploads must enter through the governed flow.

### 5.4 Storage discipline

The UI must never guess a storage path.

It must store and reuse only the canonical file URL or media reference returned by the governed upload / selection flow.

---

## 6. Storage Boundary Contract

**Status:** Partial
**Code refs:** `ifitwala_ed/utilities/file_dispatcher.py`, `ifitwala_ed/utilities/file_management.py`, `ifitwala_ed/utilities/organization_media.py`
**Test refs:** `ifitwala_ed/utilities/test_organization_media.py`

The governance contract must remain valid if the platform later separates:

* application runtime
* database
* object storage bucket

### 6.1 Stable assumptions

Allowed assumptions:

* the dispatcher returns a canonical file URL
* classification metadata lives in the database
* physical storage is abstracted behind dispatcher / file management services

Forbidden assumptions:

* website code knows the final filesystem path
* UI code builds storage URLs by string concatenation
* business logic depends on app server local disk layout

### 6.2 Public media rule

If organization media is intended for public website use:

* the storage backend may be local or bucket-based
* the canonical URL must remain renderer-safe regardless of backend
* moving from filesystem to object storage must not require block data rewrites

---

## 7. Contract Matrix

**Status:** Partial
**Code refs:** `ifitwala_ed/utilities/file_dispatcher.py`, `ifitwala_ed/utilities/governed_uploads.py`, `ifitwala_ed/utilities/organization_media.py`, `ifitwala_ed/school_settings/doctype/school/school.json`, `ifitwala_ed/school_settings/doctype/school/school.py`, `ifitwala_ed/school_settings/doctype/school/school.js`, `ifitwala_ed/school_site/doctype/gallery_image/gallery_image.json`, `ifitwala_ed/public/js/website_props_builder.js`
**Test refs:** `ifitwala_ed/utilities/test_organization_media.py`

| Area | Current state | Required state | Status |
| --- | --- | --- | --- |
| Canonical owner | School/gallery attachment patterns | Organization-owned media with optional school scope | Partial |
| Nested visibility | Not explicitly defined for media | Ancestor-to-descendant inheritance only | Partial |
| Dispatcher path | Generic dispatcher exists | Organization media must use dispatcher-only flow | Partial |
| Classification schema | Person/applicant-centric | Add explicit organization media subject/purpose contract | Implemented |
| School gallery storage | Plain attach child rows | Governed references to classified files | Partial |
| Props-builder UX | Raw image strings / attach controls without org media scope | Reuse-first media picker + governed upload | Partial |
| Storage decoupling | Architecture note says storage may change | Explicit no-local-path dependency contract | Partial |
| Tests | No organization-media governance tests | Scope, inheritance, and upload contract tests required | Partial |

Unknown rows are not allowed in this matrix. The gaps above must be resolved before implementation work is claimed complete.

---

## 8. Immediate Documentation Guardrail

**Status:** Implemented
**Code refs:** `ifitwala_ed/docs/files_and_policies/files_01_architecture_notes.md`, `ifitwala_ed/docs/files_and_policies/files_03_implementation.md`, `ifitwala_ed/docs/files_and_policies/files_04_workflow_examples.md`
**Test refs:** None

Until implementation catches up:

* do not introduce any new school/website image upload path that bypasses dispatcher governance
* do not add school-specific media pickers that treat gallery attachments as a separate file system
* do not encode local filesystem assumptions into renderer or UI logic

This document is the source of truth for future organization media implementation.
