File: ifitwala_ed/docs/AGENTS.md

# AGENTS.md — Documentation Local Rules

This file adds local rules for work inside `ifitwala_ed/docs/`.
The root `AGENTS.md` remains authoritative and must still be obeyed.

This folder is authoritative for architecture, behavior, and contract documentation.

---

## 0. Local Mission

Inside `ifitwala_ed/docs/`, prioritize:

1. documentation as source of truth
2. one canonical contract per feature
3. explicit status and code references
4. drift prevention
5. documentation that helps both humans and coding agents

Docs must reflect reality, not aspiration.

---

## 1. Canonical Documentation Rule

Each feature should have one canonical contract document.

Do not mix:

- locked behavior
- brainstorm text
- speculative notes
- draft ideas

If exploratory content is needed, keep it in a separate non-authoritative file.

Canonical docs must be clearly usable by:

- developers
- reviewers
- coding agents
- future maintainers

---

## 2. Status Marker Rule

Each major feature section should include clear status markers where applicable:

- `Status`
- `Code refs`
- `Test refs`

Avoid vague prose that does not map to implementation.

If a section cannot point to code or tests, say so explicitly.

---

## 3. Drift Control Rule

When approved implementation changes behavior:

- update the relevant canonical doc in the same change
- do not silently leave stale behavior text
- do not delete old contract text unless it is truly superseded
- if old content is replaced, mark it deprecated or point to the replacement

Drift is a bug.

---

## 4. Contract Clarity Rule

Docs must be explicit enough that a coding agent can tell:

- which files own the behavior
- which layer owns the invariant
- whether logic belongs in:
  - DocType/controller
  - API endpoint
  - SPA surface
  - scheduler/background job
  - report/dashboard
- what must not be reimplemented elsewhere

If a doc is too vague to guide safe implementation, improve the doc first.

---

## 5. Product / Security / Concurrency Coverage Rule

Canonical feature docs should explicitly state, where relevant:

- UX goals and friction reduction expectations
- permission and scope constraints
- multi-tenant isolation expectations
- concurrency/performance expectations
- queue/cache/realtime expectations when those are part of the design

Do not leave these as implicit assumptions for critical workflows.

---

## 6. Markdown Structure Rules

For docs under `ifitwala_ed/docs/docs_md/`:

- include YAML front matter with:
  - `version`
  - `last_change_date`
- update both on every change
- `## Technical Notes (IT)` must be the final top-level section
- preserve figure tags exactly

Do not break the existing docs pipeline conventions.

---

## 7. Reality-First Rule

Do not document hoped-for architecture as if it already exists.

Be precise about status:

- Implemented
- Partial
- Planned
- Deprecated

If implementation and docs disagree, stop and resolve the mismatch explicitly.

---

## 8. Documentation Delivery Checklist

Before finalizing a docs change, verify:

- the doc is canonical or clearly marked otherwise
- behavior described matches code reality
- code refs are concrete
- test refs are concrete or explicitly absent
- product/security/concurrency constraints are documented where relevant
- status is honest
- obsolete sections are retired or deprecated cleanly
- formatting/front matter/section-order rules remain valid
