# Education File Semantics And Cross-App Upload Contract

Status: Accepted and Phase 1 implemented
Date: 2026-04-15
Related current-state docs:

- `ifitwala_ed/docs/files_and_policies/files_01_architecture_notes.md`
- `ifitwala_ed/docs/files_and_policies/files_03_implementation.md`
- `ifitwala_ed/docs/curriculum/03_curriculum_materials_and_resource_contract.md`
- `ifitwala_ed/docs/docs_md/supporting-material.md`

## Bottom Line

- Keep `ifitwala_drive` strict. It should reject stale or unknown governance values.
- Keep `ifitwala_ed` responsible for education workflow semantics, tenant scope, and the meaning of each upload surface.
- `learning_resource` is now the implemented governed purpose for reusable teaching-resource workflows in both apps.
- `Supporting Material` and task resource attachments now use `learning_resource`.
- The next architecture phase should replace scattered hand-written upload dicts with one shared, versioned cross-app contract per workflow.

## Problem Statement

Recent upload failures show the same root problem:

1. file-governance enums are duplicated across code, metadata, and docs
2. current workflow builders in `ifitwala_ed` hand-author `purpose`, `slot`, `binding_role`, and retention values in many places
3. `ifitwala_drive` correctly enforces the current governed contract, but `ifitwala_ed` can drift silently until a browser upload fails
4. current semantics are not education-driven enough, especially for reusable teaching files

The concrete example is `Supporting Material`:

- product meaning: reusable instructional resource
- retired emergency-compatible purpose: `academic_report`
- implemented education meaning: `learning_resource`

`academic_report` was serviceable as a short-term compatibility purpose, but it is semantically wrong for slides, worksheets, lab handouts, readers, exemplars, and similar classroom resources.

## Education-Driven Semantic Principles

File semantics should answer: why does an education institution keep this file, who uses it, and what lifecycle governs it?

The purpose should not be:

- the UI page where the upload happened
- the temporary transport route
- the folder path
- a vague catch-all like "general"

The purpose should be stable across:

- early years and kindergarten
- K-12 schools
- community colleges
- universities

The same learner-centered meaning should survive different products and surfaces:

- a worksheet in a Grade 2 class
- a lab handout in secondary science
- a practicum guide in a community college
- a lecture deck or course reader in a university module

Those are all instructional resources. They are not academic reports.

## Proposed Semantic Boundary

### Keep `academic_report` Narrow

`academic_report` should mean a formal evaluative or progress record about learner performance.

Examples:

- report cards
- transcripts
- progress reports
- transfer or prior-school evaluations
- formal practicum evaluation summaries

It should not be the default for teacher-distributed learning files.

### Introduce `learning_resource`

Proposed purpose:

`learning_resource`

Definition:

An instructional file distributed by the institution, a teacher, or an authorized academic workflow for teaching, guided practice, revision, orientation to learning tasks, or course delivery.

Examples across education contexts:

- Early years: visual routine cards, phonics sheets, take-home caregiver guidance, story sequence cards
- K-12: lesson slides, worksheets, reading packets, lab instructions, model answers, rubric exemplars
- Community college: practical handbooks, workshop sheets, lab manuals, module readers
- University: course reader extracts, seminar slides, lab briefs, assignment guides, tutorial packs

Non-examples:

- a learner submission
- a marked script returned to a learner
- an official transcript
- a medical record
- public marketing media

## Proposed Purpose Taxonomy

This proposal does not try to redesign every purpose at once. It tightens the education layer first.

### Core learning purposes

| Purpose | Meaning | Typical owner/workflow |
| --- | --- | --- |
| `learning_resource` | reusable or distributed teaching material | `Supporting Material`, task resources, course and unit resources |
| `assessment_submission` | learner-submitted work for evaluation | task submission attachments |
| `assessment_feedback` | marked or feedback artifacts returned after evaluation | annotated files, feedback sheets, returned rubrics |
| `portfolio_evidence` | curated evidence intentionally retained in a learner portfolio | portfolio flows |
| `journal_attachment` | attachment tied to an ongoing reflective journal workflow | journal flows |
| `academic_report` | formal evaluative record about progress or achievement | transcripts, report cards, prior-school reports |

### Institutional and safeguarding purposes

| Purpose | Meaning |
| --- | --- |
| `identification_document` | identity verification documents |
| `medical_record` | medical or health evidence |
| `policy_acknowledgement` | evidence of policy acknowledgement |
| `background_check` | staff compliance evidence |
| `administrative` | operational document that does not fit a narrower governed purpose |

### Presentation and export purposes

| Purpose | Meaning |
| --- | --- |
| `student_profile_display` / `guardian_profile_display` / `employee_profile_display` / `applicant_profile_display` | controlled display image purposes |
| `organization_public_media` | public organization or school media |
| `portfolio_export` / `journal_export` | generated export artifacts |

### Reserved or exceptional purposes

| Purpose | Meaning |
| --- | --- |
| `text` | system-managed text-heavy artifact where file governance still applies |
| `other` | explicit reviewed exception, not a default authoring choice |

## Surface Mapping Proposal

| Upload surface | Current runtime purpose | Proposed target purpose | Why |
| --- | --- | --- | --- |
| `Supporting Material` file upload | `learning_resource` | `learning_resource` | reusable teaching file shared into plans, units, tasks, or class context |
| Task resource attachment | `learning_resource` | `learning_resource` | teacher-provided file that helps complete or understand work |
| Task submission attachment | `assessment_submission` | `assessment_submission` | learner work product |
| Marked or feedback attachment | `assessment_feedback` | `assessment_feedback` | returned evaluation artifact |
| Prior transcript / report card in admissions | `academic_report` | `academic_report` | formal evaluative record |
| Portfolio evidence attachment | `portfolio_evidence` | `portfolio_evidence` | curated showcase or evidence file |
| Journal attachment | `journal_attachment` | `journal_attachment` | reflective journal support file |
| School and organization logos / gallery media | `organization_public_media` | `organization_public_media` | public presentation media |

## Cross-App Architecture Proposal

### Current Weakness

The current Ed to Drive contract is too string-oriented:

- workflow modules build classification dicts manually
- the same semantic values are duplicated in metadata, docs, Ed code, and Drive code
- browser-time failures become the first real integration test

### Proposed Model: `GovernedUploadSpec`

Each governed upload workflow should have one canonical spec keyed by a workflow identifier.

Examples:

- `supporting_material.file`
- `task.resource`
- `task.submission`
- `admissions.applicant_document`
- `admissions.applicant_profile_image`
- `organization_media.school_logo`

Each spec should define:

- contract version
- owner doctype/name resolver
- attached doctype/name resolver
- primary subject resolver
- data class
- purpose
- retention policy
- slot resolver
- binding role
- context override and folder hints
- optional MIME restrictions
- optional post-finalize callback identifier

### Authority Split

`ifitwala_ed` should own:

- education semantics
- workflow meaning
- tenant and role scope
- record ownership
- slot resolution
- which users can author or read a file in product context

`ifitwala_drive` should own:

- upload session lifecycle
- temporary object storage
- binary finalize flow
- governed storage placement
- final validation against the canonical spec

### Recommended Implementation Shape

Option A, preferred:

- move workflow specs into a shared package used by both apps

Option B:

- Ed exports a machine-readable contract snapshot consumed by Drive

Either way, Drive should validate against the same canonical workflow spec that Ed used to create the session.

## Contract-Versioned Upload Sessions

Each upload session should persist:

- `workflow_id`
- `contract_version`
- resolved classification payload
- resolved slot
- resolved binding role
- resolved subject and scope data

Finalize should fail only when:

- the session no longer matches the authoritative business record
- the contract version is no longer supported
- the file bytes or MIME are invalid

This is better than comparing many ad hoc strings assembled in multiple modules.

## Current Implementation Status

Implemented in this rollout:

- `learning_resource` added to the canonical Ed purpose registry
- `learning_resource` added to the governed metadata enums used by `File Classification` and applicant document configuration
- `Supporting Material` upload builders moved from `academic_report` to `learning_resource`
- task resource upload builders moved from `academic_report` to `learning_resource`
- Drive-side session and file validation now rejects unknown purposes explicitly, including stale teaching-resource aliases

Intentionally not changed in this rollout:

- admissions, transcript, report-card, and other evaluative workflows that still belong on `academic_report`
- existing binding-role names such as `general_reference`, which remain a compatibility layer until Drive binding semantics are separately normalized

## Documentation Proposal

The docs should separate:

1. current runtime contract
2. proposed semantic evolution
3. workflow-specific mapping tables

Recommended doc set:

- one canonical current-state enum and contract doc
- one education-oriented semantics doc
- one "how to add a governed upload flow" implementation checklist
- one parity checklist for Ed + Drive deploy verification

Docs should stop repeating enum lists in many places unless they are generated or explicitly synchronized.

## Testing Proposal

Add these regression guardrails:

1. Enum parity test
- assert the allowed purpose set matches `File Classification` metadata
- assert Ed and Drive agree on that set

2. Workflow contract tests
- one unit test per governed upload workflow that checks the resolved contract payload

3. Cross-app finalize tests
- stale purpose, slot, or subject values fail with structured errors before user-facing release

4. Doc drift checks
- high-signal docs that list enums or workflow mappings should be checked against the canonical source

## Error Handling Proposal

Drive validation errors should return structured fields such as:

- `workflow_id`
- `field`
- `expected`
- `received`
- `contract_version`

Ed should translate those into concise user-facing errors such as:

- "This upload flow is out of date for teaching resources. Refresh and try again."
- "This file no longer matches the current class resource contract."

The browser should not receive a raw mixed message assembled from low-level exceptions.

## Rollout Status

### Completed in this rollout

- retired the stale `general_reference` purpose usage in Ed teaching-resource builders
- added `learning_resource` to the canonical purpose set
- updated File Classification and applicant document metadata to the canonical purpose catalog
- updated Drive validators and governed file models to reject unknown purposes explicitly
- migrated `Supporting Material` and task resource workflows to `learning_resource`
- added parity and regression tests across both repos

### Next architecture phase

Cross-app change:

- replace hand-written workflow dicts with shared `GovernedUploadSpec` definitions
- add deploy-time parity checks and contract snapshots so Ed and Drive cannot drift silently

## Recommendation

Accepted semantic direction:

- `learning_resource` as the education-oriented teaching-resource purpose
- strict Drive validation retained
- shared workflow-spec contract as the long-term integration model

This rollout gives the repo a clearer education-first file model now and defines the next contract-centralization phase without keeping stale emergency guidance in the canonical note.
