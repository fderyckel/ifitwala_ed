# Student Portfolio + Journal Architecture (Students Module)

Status: Implemented v1
Last updated: 2026-02-12

## 1. Scope and placement

Portfolio and journaling are implemented in the `Students` module and surfaced in SPA pages under:

- `ui-spa/src/pages/student/StudentPortfolioFeed.vue`
- `ui-spa/src/pages/guardian/GuardianPortfolioFeed.vue`
- `ui-spa/src/pages/staff/StaffPortfolioFeed.vue`

The frontend uses a shared feed surface (`PortfolioFeedSurface.vue`) with role-specific filter constraints.

## 2. Core principle

Portfolio is an annual curation layer over existing evidence and reflection streams:

- Existing assessed evidence source: `Task Submission`
- New universal reflection stream: `Student Reflection Entry`
- Optional governed external artefact source: `File` (dispatcher/classification required)

Guardians and external viewers are constrained to showcase-approved portfolio items only.

## 3. Data model

### New doctypes

- `Student Portfolio`
  - Unique scope: `student + academic_year + school`
  - Child table: `Student Portfolio Item`
- `Student Portfolio Item` (child)
  - Exactly one source reference per row:
    - `task_submission` or
    - `student_reflection_entry` or
    - `artefact_file`
  - Includes showcase and moderation fields
- `Student Reflection Entry`
  - Universal context anchors (course, student_group, program_enrollment, activity_booking, lesson, lesson_instance, lesson_activity, task_delivery, task_submission)
- `Tag Taxonomy`
  - Controlled school/framework taxonomy with optional `Learning Standards` linkage
- `Evidence Tag`
  - Applied tag instance with attribution (`tagged_by_type`, `tagged_by_id`) and polymorphic target
- `Portfolio Share Link`
  - Token hash at rest, expiry, revocation, optional viewer-email gate, showcase-only scope
- `Portfolio Journal Settings`
  - School-scoped controls (moderation/share/export)
  - Child table: `Portfolio Journal Setting Role`

## 4. Relationship to existing ERP model

Portfolio/Journal attaches to existing ERP entities without duplication:

- `Task Submission`: canonical assessed evidence container
- `Task Delivery`: assignment context anchor for reflections
- `Lesson`, `Lesson Instance`, `Lesson Activity`: instructional context anchors for reflections
- `Course`, `Student Group`: classroom context anchors
- `Program Enrollment`: program-level context and filtering
- `Academic Year`: annual portfolio boundary
- `Student`: primary subject and ownership scope
- `Guardian`: read-only showcase visibility through guardian portal
- `Activity Booking`: co-curricular reflection context

## 5. Visibility and moderation contract

- Student: read/write own reflection and portfolio records
- Guardian: showcase-approved portfolio items only for linked children
- Staff: scoped by existing school/relationship authorization
- External share: tokenized, expiring, revocable public route (`/portfolio/share/<token>`) with optional email restriction

Moderation is school-setting controlled. Default configuration is moderation enabled for showcase flow.

Staff moderation workload control:

- Batch moderation is supported for showcase portfolio items (`approve`, `return_for_edit`, `hide`).
- Batch actions are blocked when school settings disable moderation or disable showcase moderation scope.
- Moderation role checks use `Portfolio Journal Settings.moderation_roles` (with admin-role override).

## 6. API contract

Backend endpoints are grouped under:

- `ifitwala_ed.api.student_portfolio`

Key contracts:

- `get_portfolio_feed`
- `create_reflection_entry`, `list_reflection_entries`
- `add_portfolio_item`, `update_portfolio_item`, `set_showcase_state`
- `moderate_portfolio_items` (batch showcase moderation)
- `apply_evidence_tag`, `remove_evidence_tag`
- `create_portfolio_share_link`, `revoke_portfolio_share_link`
- `export_portfolio_pdf`, `export_reflection_pdf`

SPA service layer:

- `ui-spa/src/lib/services/portfolio/portfolioService.ts`

Type contracts:

- `ui-spa/src/types/contracts/portfolio/*`

## 7. File governance and GDPR

Portfolio/journal evidence and exports must use dispatcher governance.

Added `File Classification.purpose` options:

- `portfolio_evidence`
- `journal_attachment`
- `portfolio_export`
- `journal_export`

Expected slots:

- `portfolio_artefact`
- `journal_attachment`
- `portfolio_export_pdf`
- `journal_export_pdf`

Exports are generated as governed files with:

- `retention_policy = immediate_on_request`

No direct `File.insert()` is permitted in portfolio/journal business flows.

## 8. Guardian publication terminology alignment

Guardian results publication terminology is standardized to:

- `Task Outcome.is_published`

Legacy references to `published_to_parents` are considered stale and should not be used for new work.
