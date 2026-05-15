---
title: "Material Placement: Shared Context For Supporting Materials"
slug: material-placement
category: Curriculum
doc_order: 9
version: "1.5.1"
last_change_date: "2026-04-25"
summary: "Place reusable supporting materials into shared plans, class plans, sessions, and tasks without duplicating the underlying material."
seo_title: "Material Placement: Shared Context For Supporting Materials"
seo_description: "Place reusable supporting materials into shared plans, units, class sessions, and tasks without duplicating the underlying material."
---

## Material Placement: Shared Context For Supporting Materials

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/material_placement/material_placement.json`, `ifitwala_ed/curriculum/doctype/material_placement/material_placement.py`, `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/hooks.py`
Test refs: `ifitwala_ed/curriculum/test_materials.py`, `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`

`Material Placement` is the contextual share record for a [**Supporting Material**](/docs/en/supporting-material/). It answers where students see a material and how that placement should behave.

## Before You Start (Prerequisites)

Status: Implemented
Code refs: `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/curriculum/doctype/material_placement/material_placement.py`
Test refs: `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`

- Create the `Supporting Material` first.
- Choose a valid curriculum anchor:
  - `Course Plan`
  - `Unit Plan`
  - `Class Teaching Plan`
  - `Class Session`
  - `Task`
- Keep the anchor inside the same authoritative course as the material.

## Where It Is Used Across The ERP

Status: Partial
Code refs: `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/teaching_plans.py`, `ifitwala_ed/api/courses.py`, `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`, `ifitwala_ed/ui-spa/src/pages/staff/CoursePlanWorkspace.vue`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/api/test_teaching_plans.py`, `ifitwala_ed/api/test_courses.py`, `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`

- Task-overlay authoring creates task placements.
- Staff planning now creates and removes class-wide and session-specific placements inline from the class-planning SPA.
- Shared course planning now creates and removes course-plan and unit-plan placements inline from the shared curriculum workspace.
- The staff class-planning SPA and the student LMS learning space both read placements through the bounded teaching-plan payload.
- File access still resolves on the material owner, but open URLs are now placement-aware so class-owned materials stay scoped to the right class/session context.

## Lifecycle And Linked Documents

Status: Implemented
Code refs: `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/api/materials.py`
Test refs: `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`

1. A reusable `Supporting Material` exists.
2. A `Material Placement` shares it into a curriculum context.
3. Removing the share deletes the placement only.
4. The underlying material remains reusable until explicitly archived or deleted.

## Permission Matrix

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/material_placement/material_placement.json`, `ifitwala_ed/curriculum/doctype/material_placement/material_placement.py`, `ifitwala_ed/curriculum/materials.py`
Test refs: `ifitwala_ed/curriculum/test_materials.py`, `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`

| Role | Read | Write | Create | Delete | Notes |
|---|---|---|---|---|---|
| `System Manager` | Yes | Yes | Yes | Yes | Global administrative access |
| `Academic Admin` | Yes | Yes | Yes | Yes | Global academic access |
| `Instructor` | Yes | Yes | Yes | Yes | Limited by taught-course or class anchor scope |
| `Curriculum Coordinator` | Yes | Yes | Yes | No | Write applies to shared curriculum placements on `Course Plan` and `Unit Plan`; class-owned anchors remain instructor/class-scoped |
| `Accreditation Visitor` | No | No | No | No | Not in the live material-placement runtime access contract |

## Related Docs

<RelatedDocs
  slugs="supporting-material,unit-plan,class-session,task"
  title="Related Documentation"
/>

## Technical Notes (IT)

Status: Partial
Code refs: `ifitwala_ed/curriculum/doctype/material_placement/material_placement.json`, `ifitwala_ed/curriculum/doctype/material_placement/material_placement.py`, `ifitwala_ed/curriculum/materials.py`
Test refs: `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`

### Schema And Controller Snapshot

- **DocType schema file**: `ifitwala_ed/curriculum/doctype/material_placement/material_placement.json`
- **Controller file**: `ifitwala_ed/curriculum/doctype/material_placement/material_placement.py`
- **Key fields**:
  - `supporting_material`
  - `course`
  - `anchor_doctype`
  - `anchor_name`
  - `origin`
  - `usage_role`

### Current Contract

- Placement does not own the file.
- Placement does not duplicate the underlying material.
- Placement course must match the authoritative course on both the material and the anchor.
- Duplicate share of the same material into the same anchor is rejected.
- Shared-plan resources are course-readable, while class-owned placements are now scoped through the class plan or class session anchor.
- Program-scoped curriculum coordinators can create and edit shared-plan placements on `Course Plan` and `Unit Plan`, but they do not gain class-owned placement write access through coordinator scope alone.

### Current Constraints To Preserve In Review

- Removing a placement means unshare, not delete.
- Do not use placement as a fake session-only library.
- Keep class-shared persistence anchored onto real curriculum objects such as `Class Teaching Plan` or `Class Session`.
