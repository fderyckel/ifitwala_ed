# Codebase Maintainability Contract

Status: Active
Code refs: `AGENTS.md`, `ifitwala_ed/api/AGENTS.md`
Test refs: `scripts/test_metrics.sh`
Last updated: 2026-05-29

This note defines repository-wide maintainability rules for large files and API implementation ownership.

It does not authorize behavior changes by itself. Refactors must still preserve product UX, security, data integrity, multi-tenant isolation, public contracts, and documented runtime behavior.

## Large File Rule

Any file over 1000 lines is a maintainability risk.

When touching or inspecting a file over that threshold, agents should identify whether the current task is a narrow fix or a structural refactor.

For a narrow fix:

- keep the change scoped to the requested behavior
- do not opportunistically reorganize unrelated code
- call out a follow-up refactor proposal when the large file makes future maintenance risky

For a refactor:

- make a proposal before moving code
- identify current responsibilities in the file
- identify natural extraction boundaries
- define the target module or component layout
- list public imports, whitelisted paths, hooks, jobs, scripts, and tests that must stay stable
- describe migration steps that reduce risk
- get explicit approval before making structural changes unless the user has already approved that refactor

## API Folder Direction

`ifitwala_ed/api/` is the public Frappe RPC boundary, not the default home for domain implementation code.

Root API modules should become thin facades that preserve stable dotted paths such as `ifitwala_ed.api.inquiry.get_dashboard_data`.
Domain implementation should live in the owning package, such as `ifitwala_ed/admission/api/`, `ifitwala_ed/assessment/api/`, `ifitwala_ed/curriculum/api/`, `ifitwala_ed/schedule/api/`, `ifitwala_ed/students/api/`, `ifitwala_ed/governance/api/`, `ifitwala_ed/accounting/api/`, or `ifitwala_ed/hr/api/`.

Rules:

- preserve public Frappe method paths unless an explicit endpoint contract migration is approved
- keep whitelisted decorators on the public facade only unless the domain contract intentionally exposes another route
- move implementation one domain at a time
- avoid duplicate runtime workflows between old and new modules
- move tests with ownership, leaving root API tests only for facade, payload-binding, and compatibility coverage
- update docs and explicit test-module lists when ownership or paths change

## Refactor Priority

Prefer these first:

1. Files that already have clear facade and implementation boundaries.
2. Files where tests already cover the behavior being moved.
3. Domain clusters with obvious ownership and canonical docs.
4. Large cross-cutting files only after their contracts and permission tests are explicit.

High-risk files, especially governed-file, private-media, guest-facing, hook-bound, and website-route modules, require extra permission and contract review before splitting.
