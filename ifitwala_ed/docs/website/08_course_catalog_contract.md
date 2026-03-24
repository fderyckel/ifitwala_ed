<!-- ifitwala_ed/docs/website/08_course_catalog_contract.md -->
# Course Catalog And Course Detail Contract

**Audience:** Product, marketing, admissions, website implementers
**Scope:** Public school website only
**Status (March 23, 2026):** Planned, approved product direction; not implemented
**Authority:** Subordinate to
* `ifitwala_ed/docs/website/01_architecture_notes.md`
* `ifitwala_ed/docs/high_concurrency_contract.md`
* `ifitwala_ed/docs/docs_md/course.md`

---

## 0. Bottom-Line Contract

Ifitwala_Ed should support a **public course catalog** and **public course detail pages** for prospective applicants, families, and community members.

This surface is:

* **marketing and PR**, not LMS
* **school-scoped**, not global by default
* **curated**, not a raw projection of instructional records
* **workflow-published**, not auto-public from academic truth alone

Hard boundary:

> Public course publishing may expose course identity, overview, aims, and curated learning highlights.
> It must never expose raw instructional delivery, unpublished lesson flow, assignments, submissions, grading execution, or student-specific learning state.

---

## 1. Product Goal

Schools need to present their academic offering clearly to:

* prospective applicants
* prospective families
* community members
* accreditation and external reviewers when appropriate

The product goal is to replace static or fragmented course descriptions with:

* a school-branded, searchable public course catalog
* curated course detail pages
* clear academic storytelling aligned with admissions intent

This is not a staff workflow tool and not a student execution surface.

---

## 2. Public / Private Boundary (Locked)

### 2.1 Publicly allowed

Public course publishing may include:

* course name
* school context
* public course slug
* hero image / supporting image
* short description
* longer course overview
* course aims / outcomes at a high level
* broad assessment approach summary
* curated learning highlights derived from course structure
* related program context when appropriate
* admissions-facing CTA

### 2.2 Publicly forbidden

Public course publishing must not expose:

* assignments
* task delivery state
* task outcomes
* unpublished learning units or lessons as raw truth
* student activity, progress, or pacing
* teacher-only notes
* rubric execution details
* live grading / marks / attendance / portal-only data
* internal operational fields whose meaning is only valid inside ERP/LMS flows

### 2.3 Learning-unit rule

`Learning Unit` data is not public website truth.

If the public page includes learning-unit-like content, it must be presented as **curated highlights**:

* short title
* short summary
* optional image
* optional sequence order

It must not behave like a portal syllabus, lesson map, or LMS module tree.

---

## 3. Route Ownership (Planned)

Planned routes:

| Route | Owner | Purpose | Status |
| --- | --- | --- | --- |
| `/schools/{school_slug}/courses` | custom website renderer | school-scoped course catalog | Planned |
| `/schools/{school_slug}/courses/{course_slug}` | custom website renderer | school-scoped public course detail page | Planned |

Rules:

* Routes remain under `/schools/...` in line with locked website routing.
* No root-level course slugs.
* Course detail routes are school-scoped because the public presentation is school-owned.

---

## 4. Data Model Direction (Planned)

### 4.1 New public presentation record

Introduce a new public publishing DocType:

* `Course Website Profile`

Purpose:

* keep `Course` as academic/catalog truth
* keep public storytelling, workflow, and SEO on a dedicated website-owned record

### 4.2 Proposed minimal fields

`Course Website Profile`

* `school`
* `course`
* `course_slug`
* `status`
* `workflow_state`
* `seo_profile`
* `hero_image`
* `intro_text`
* `overview_html`
* `aims_html`
* `assessment_summary_html`
* `learning_highlights`
* `blocks`

Notes:

* `course_slug` should live on `Course Website Profile`, not `Course`.
* Public route ownership is school-scoped and belongs to the website surface.
* Keeping the slug on the website profile avoids mixing public CMS identity into the academic truth record prematurely.

### 4.3 Learning highlights child table

If a child table is introduced, it must remain presentation-only.

Allowed fields:

* `title`
* `summary`
* `image`
* `display_order`

No business logic belongs in the child table.

---

## 5. Workflow Contract (Planned)

Workflow mirrors the rest of the website system:

* `Draft`
* `In Review`
* `Approved`
* `Published`

Publication rules:

* `Course` academic truth does not by itself make a public page visible
* the website profile must also be workflow-published
* the school must be website-published
* the course detail page must be school-scoped

This preserves the locked product split:

* curriculum truth in academic records
* public marketing truth in website records

---

## 6. Defaulting / Friction-Reduction Contract (Planned)

First-time course publication should auto-fill missing defaults only.

The system may prepare, when blank:

* `course_slug` from `course_name`
* `hero_image` from `Course.course_image`
* `intro_text` from `Course.description`
* `overview_html` from curated website fields if later introduced
* `seo_profile`
* starter blocks for the detail page

The system must not overwrite authored website content.

### 6.1 Proposed SEO defaults

When missing:

* `meta_title` = course name
* `meta_description` = trimmed intro/description
* `og_title` = meta title
* `og_description` = meta description
* `og_image` = hero image or course image
* `canonical_url` = full school-scoped course route
* `noindex = 0`

---

## 7. Catalog Surface Contract (Planned)

### 7.1 Public catalog purpose

The catalog page is the **discovery surface**.

It should help visitors quickly answer:

* what courses does this school offer?
* how are courses grouped?
* which courses are relevant to my child or interest?

### 7.2 Catalog output shape

Each card/list item should support:

* course title
* short intro
* image
* course group / subject area
* optional related program labels
* detail URL

### 7.3 Planned filtering

Recommended public filters:

* `Course Group (Catalog)`
* related program
* school
* term-long flag only if product decides it is meaningful publicly

Do not expose purely internal academic setup fields as public filters unless product explicitly approves them.

### 7.4 School scope

The default catalog is school-scoped.

This preserves:

* sibling isolation
* school-specific presentation
* the product expectation that a school website markets that school's offering

---

## 8. Course Detail Page Contract (Planned)

### 8.1 Recommended baseline sections

Minimum recommended structure:

1. `course_intro` block (owns H1)
2. `rich_text` overview / aims
3. `learning_highlights` block
4. `cta` block

Optional later sections:

* related programs
* faculty snapshot
* FAQ

### 8.2 Content posture

The course page should answer:

* what is this course about?
* why would a student take it?
* what big ideas or experiences does it include?
* how does it fit into the broader school offering?

It should not read like a live syllabus or LMS dashboard.

---

## 9. Provider And Block Direction (Planned)

### 9.1 Providers

Planned shared/page providers:

* `get_school_courses`
* `get_course_catalog_page_context`
* `get_course_page_context`

Provider rules remain unchanged:

* trusted app-owned code only
* read-only
* stable payloads
* no tenant-authored logic

### 9.2 Proposed blocks

Planned new blocks:

* `course_catalog`
* `course_intro`
* `learning_highlights`

Block responsibilities:

* `course_catalog` renders discovery grid/list from provider output
* `course_intro` owns the H1 and course hero story
* `learning_highlights` renders curated marketing-friendly unit summaries

No block should query raw instructional data directly.

---

## 10. Permissions And Isolation

Server-side rules must enforce:

* only website-published schools can expose public catalog/course pages
* only published `Course Website Profile` records are publicly visible
* a course detail page is visible only for the school that owns the website profile
* sibling schools must not leak each other's course pages through broad queries

If a course is reused academically across schools, each school still owns its own public presentation.

---

## 11. Concurrency And Request-Shape Rules

This surface is public and potentially hot.

Implementation must follow the repo concurrency contract:

* one bounded catalog request per page
* one bounded course-detail request per page
* no client request waterfalls
* no per-card follow-up queries
* cache only where scope and invalidation are explicit

Preferred pattern:

* a cached provider for school-scoped published course summaries
* a separate cached provider for school + course detail

Avoid:

* building the catalog from repeated per-course `get_doc(...)`
* exposing raw learning-unit trees and then reshaping them client-side
* unscoped caches that can leak across schools

---

## 12. Relationship To Existing Academic Records

`Course` remains:

* catalog-level academic truth
* enrollment/reference anchor
* assessment configuration anchor

`Course Website Profile` would become:

* public storytelling layer
* SEO owner
* workflow publication owner
* school-specific presentation owner

This split is intentional and should remain canonical.

---

## 13. Implementation Phasing

### Phase 1

* `Course Website Profile`
* school-scoped course routes
* course catalog page
* course detail page
* SEO/default preparation
* admissions-facing CTA

### Phase 2

* curated `learning_highlights`
* related program display
* optional faculty snapshot

### Phase 3

* richer catalog filtering
* featured courses
* optional accreditation/public-program framing if product requires it

---

## 14. Status, Code Refs, Test Refs

### Status

* Product direction: Approved
* Documentation status: Canonical planned contract
* Implementation status: Not started

### Code refs

Current related implementation surfaces only:

* `ifitwala_ed/docs/website/01_architecture_notes.md`
* `ifitwala_ed/website/renderer.py`
* `ifitwala_ed/website/block_registry.py`
* `ifitwala_ed/school_site/doctype/school_website_page/*`
* `ifitwala_ed/school_site/doctype/program_website_profile/*`
* `ifitwala_ed/docs/docs_md/course.md`

No `Course Website Profile`, course catalog route, or public course-detail implementation exists yet.

### Test refs

None yet.

Tests must be added only when implementation starts.

---

## 15. Non-Goals

This contract does not cover:

* LMS lesson delivery
* student or guardian portal course views
* public application workflow state
* public publication of assignments, marks, or live curriculum execution

---

## 16. One-Line Rule

> Public course pages are school-scoped curriculum marketing surfaces with curated academic storytelling; instructional execution remains private to portal/LMS workflows.
