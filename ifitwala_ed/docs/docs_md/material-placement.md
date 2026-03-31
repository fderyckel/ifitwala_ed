---
title: "Material Placement: Shared Context For Supporting Materials"
slug: material-placement
category: Curriculum
doc_order: 9
version: "1.0.2"
last_change_date: "2026-03-31"
summary: "Place reusable supporting materials into course, unit, lesson, and task contexts without duplicating the underlying material."
seo_title: "Material Placement: Shared Context For Supporting Materials"
seo_description: "Place reusable supporting materials into course, unit, lesson, and task contexts without duplicating the underlying material."
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
  - `Course`
  - `Learning Unit`
  - `Lesson`
  - `Task`
- Keep the anchor inside the same authoritative course as the material.

## Where It Is Used Across The ERP

Status: Partial
Code refs: `ifitwala_ed/api/materials.py`, `ifitwala_ed/api/courses.py`, `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
Test refs: `ifitwala_ed/api/test_courses.py`, `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`

- Task-overlay authoring creates task placements.
- The student course LMS reads placements to build the visible materials shelf.
- File access still resolves on the material owner, while placement only defines context and visibility.

## Lifecycle And Linked Documents

Status: Implemented
Code refs: `ifitwala_ed/curriculum/materials.py`, `ifitwala_ed/api/materials.py`
Test refs: `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`

1. A reusable `Supporting Material` exists.
2. A `Material Placement` shares it into a curriculum context.
3. Removing the share deletes the placement only.
4. The underlying material remains reusable until explicitly archived or deleted.

## Related Docs

Status: Implemented
Code refs: None (documentation cross-reference section)
Test refs: `ifitwala_ed/curriculum/doctype/material_placement/test_material_placement.py`

- [**Supporting Material**](/docs/en/supporting-material/)
- [**Task**](/docs/en/task/)
- [**Lesson Activity**](/docs/en/lesson-activity/)

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
- Desk read/list visibility follows the placement course, and curriculum coordinators are read-only by default.

### Current Constraints To Preserve In Review

- Removing a placement means unshare, not delete.
- Do not use placement as a fake session-only library.
- Keep class-shared persistence anchored onto real curriculum objects.
