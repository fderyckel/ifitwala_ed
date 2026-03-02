# Admissions Residual Decisions

Date: 2026-03-02

This note replaces prior admission audit working files. Most audit items are implemented. The remaining items are explicit product/architecture decisions.

## 1) Admissions Communication Contract

Resolved on 2026-03-02:
- Admissions communication now runs as applicant/staff case threads anchored to `Student Applicant` context.
- Staff triage is surfaced in `Admissions Cockpit` via communication summaries (`unread`, `last preview`, `needs_reply`).
- Applicant-facing communication is surfaced in portal route `/admissions/messages`.
- Thread read/write APIs are centralized in `ifitwala_ed.api.admissions_communication`.

## 2) Student Direct-Creation Guard Policy

Decision required:
- Keep `allow_direct_creation` as an explicit exceptional bypass, or
- Remove that bypass and enforce promotion/import/migration/patch-only creation.

Why this is still open:
- Current Student controller allows `allow_direct_creation`, while some Phase 03 audit language states stricter creation constraints.

## 3) Optional UX/Performance Follow-Up

Not a blocker, but still candidate work:
- Make Desk `Review Snapshot` issue lines directly actionable with deep links.
- Add measured caching strategy for `get_readiness_snapshot` only if profiling shows meaningful latency.
