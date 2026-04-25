---
title: "Group Message: Scoped Message Draft for Group Audiences"
slug: group-message
category: Schedule
doc_order: 5
version: "1.0.0"
last_change_date: "2026-03-29"
summary: "Store a message draft scoped to one or more scheduling dimensions such as program, course, cohort, or student group, with an optional guardian-visibility flag."
seo_title: "Group Message: Scoped Message Draft for Group Audiences"
seo_description: "Store a message draft scoped to one or more scheduling dimensions such as program, course, cohort, or student group."
---

## Group Message: Scoped Message Draft for Group Audiences

`Group Message` is a thin Schedule-domain message record. In the current workspace it is schema-only: it stores a message title and body plus optional audience anchors such as program, course, cohort, and student group.

## Before You Start (Prerequisites)

- Decide the audience anchor before creating the message:
  - `program`
  - `course`
  - `cohort`
  - `student_group`
- Decide whether the message should be visible to guardians.

## Why It Matters

- It gives staff a place to persist a group-scoped message payload instead of free text outside the ERP.
- It keeps audience context attached to the message draft.

## Where It Is Used Across the ERP

No controller-driven consumers were located in the current workspace beyond the doctype itself. At present this page should be treated as a schema contract rather than a workflow contract.

## Lifecycle and Linked Documents

1. Create the message.
2. Set one or more audience anchors as needed.
3. Enter `message_title`, `message`, and optional guardian visibility.

## Related Docs

<RelatedDocs
  slugs="student-group,student-cohort"
  title="Related Docs"
/>

## Technical Notes (IT)

### Schema and Controller Snapshot

- **DocType schema file**: `ifitwala_ed/schedule/doctype/group_message/group_message.json`
- **Controller file**: `ifitwala_ed/schedule/doctype/group_message/group_message.py`
- **Key fields**:
  - `message_title`
  - `message`
  - `visible_to_guardians`
  - `program`
  - `course`
  - `cohort`
  - `student_group`
- **Lifecycle hooks in controller**:
  - none beyond the base `Document` implementation

### Current Contract

- `Group Message` currently has no custom controller logic.
- The doctype is effectively a scoped content container.
- Audience semantics are represented by link fields rather than controller-enforced delivery behavior.

### Permission and Visibility Notes

- Current schema permissions grant full access only to `System Manager`.
- `visible_to_guardians` is a stored flag only; I did not find a current runtime consumer in this workspace that publishes the message to guardians automatically.

### Current Constraints To Preserve In Review

- Do not document delivery or notification behavior that does not exist in code.
- If this doctype gains an outbound communication role later, update this page together with the relevant messaging workflow docs.
