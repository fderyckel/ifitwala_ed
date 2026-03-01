# Admissions Residual Decisions

Date: 2026-03-01

This note replaces prior admission audit working files. Most audit items are implemented. The remaining items are explicit product/architecture decisions.

## 1) Admissions Communication Contract

Decision required:
- Introduce a first-class `Admissions Communication` artifact for applicant/inquiry lifecycle communications, or
- Formally standardize on existing `Org Communication` patterns and update admission contracts/docs accordingly.

Why this is still open:
- Admission docs reference `Admissions Communication` surfaces, but no admissions-specific implementation path is currently present.

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
