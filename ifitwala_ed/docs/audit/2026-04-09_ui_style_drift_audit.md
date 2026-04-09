# UI Style Drift Audit

**Date:** 2026-04-09
**Status:** Audit note, not a canonical behavior contract
**Scope:** `ifitwala_ed/ui-spa/` route pages, layouts, shared CSS, and agent workflow notes
**Reference docs:**
- `AGENTS.md`
- `ifitwala_ed/ui-spa/AGENTS.md`
- `ifitwala_ed/docs/spa/01_spa_architecture_and_rules.md`
- `ifitwala_ed/docs/spa/02_style_note.md`

---

## Bottom Line

- The repo already has a real UI system: `tokens.css`, `app.css`, `layout.css`, `components.css`, canonical SPA notes, and local agent rules.
- The current patchwork comes from drift in usage, not from missing architecture.
- The highest-risk drift vectors are now: shell/layout bypasses, raw palette utilities in page templates, and page-local scoped CSS carrying visual decisions.
- The undefined semantic utilities and stray CSS vars found in the initial audit have been removed, and the style-drift baseline is now intentionally empty.
- The immediate goal should be to stop new drift, document the page-family rules more explicitly, and migrate the worst exceptions in controlled batches.

---

## Audit Evidence

- `59` route/page Vue files live under `ifitwala_ed/ui-spa/src/pages/`.
- `25` Vue style blocks exist under `ui-spa/src`; `22` are scoped.
- `9` page files currently contain local `<style scoped>` blocks.
- At least `3` page files use scoped CSS for visual styling, not just layout:
  - `ifitwala_ed/ui-spa/src/pages/staff/analytics/AttendanceLedger.vue`
  - `ifitwala_ed/ui-spa/src/pages/staff/analytics/EnrollmentAnalytics.vue`
  - `ifitwala_ed/ui-spa/src/pages/staff/analytics/StudentLogAnalytics.vue`
- `34` routed pages use raw Tailwind palette utilities (`slate-*`, `gray-*`, `amber-*`, etc.) inside page templates.
- Undefined semantic utilities and stray CSS vars detected in the first audit pass were normalized in the follow-up cleanup. The guardrail baseline is now empty.

---

## Findings

### 1. Canonical style architecture exists, but some layout shells bypass it

**Code refs**
- `ifitwala_ed/ui-spa/src/style.css`
- `ifitwala_ed/ui-spa/src/styles/tokens.css`
- `ifitwala_ed/ui-spa/src/styles/layout.css`
- `ifitwala_ed/ui-spa/src/styles/components.css`
- `ifitwala_ed/ui-spa/src/layouts/PortalLayout.vue`
- `ifitwala_ed/ui-spa/src/layouts/StaffPortalLayout.vue`

**What is happening**
- `StaffPortalLayout.vue` is aligned with the shared shell classes.
- `PortalLayout.vue` still embeds its main background and shell treatment inline in the template.

**Implication**
- The codebase has two competing sources of truth for shell styling: canonical CSS files and inline layout composition.

### 2. Route root shells are not normalized across surfaces

**Staff**
- Canonical roots already in use: `staff-shell`, `analytics-shell`, `gradebook-shell`
- Drift candidates still using page-local padding roots:
  - `ifitwala_ed/ui-spa/src/pages/staff/ProfessionalDevelopment.vue`
  - `ifitwala_ed/ui-spa/src/pages/staff/admissions/AdmissionsCockpit.vue`
  - `ifitwala_ed/ui-spa/src/pages/staff/analytics/StudentDemographicAnalytics.vue`
  - `ifitwala_ed/ui-spa/src/pages/staff/analytics/StudentOverview.vue`
  - `ifitwala_ed/ui-spa/src/pages/staff/schedule/student-groups/StudentGroups.vue`

**Student / Guardian**
- Many pages use the expected rhythm-only roots (`space-y-*`).
- A smaller set still owns page-level padding locally:
  - `ifitwala_ed/ui-spa/src/pages/student/Courses.vue`
  - `ifitwala_ed/ui-spa/src/pages/student/StudentLogs.vue`
  - `ifitwala_ed/ui-spa/src/pages/student/CourseDetail.vue`
  - `ifitwala_ed/ui-spa/src/pages/student/StudentQuiz.vue`

**Implication**
- Agents do not have a clear enough page-family shell rule, so new pages can look “correct” while still drifting from the surface contract.

### 3. Shared primitives are present, but page templates still choose their own visual language

**Good shared primitives already exist**
- `card-surface`
- `paper-card`
- `analytics-shell`
- `analytics-card`
- `action-tile`
- `mini-kpi-card`
- `if-action`
- `portal-sidebar*`

**Representative drift examples**
- `ifitwala_ed/ui-spa/src/pages/student/Courses.vue`
- `ifitwala_ed/ui-spa/src/pages/student/StudentLogs.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/RoomUtilization.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/schedule/student-groups/StudentGroups.vue`

**Implication**
- The same surface can alternate between semantic component classes and raw palette-heavy template styling, which creates the “patchwork” feel.

### 4. Initial semantic-token drift has been normalized, and must not return

**Code refs**
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianAttendance.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianMonitoring.vue`
- `ifitwala_ed/ui-spa/src/pages/guardian/GuardianPolicies.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/StaffPolicies.vue`
- `ifitwala_ed/ui-spa/src/overlays/staff/StaffPolicyInformOverlay.vue`
- `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantDocuments.vue`
- `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantPolicies.vue`
- `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantSubmit.vue`
- `ifitwala_ed/ui-spa/src/components/communication/OrgCommunicationQuickCreateModal.vue`
- `ifitwala_ed/ui-spa/src/pages/student/StudentLogs.vue`
- `ifitwala_ed/ui-spa/src/overlays/planning/QuickClassSessionOverlay.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/ClassPlanning.vue`
- `ifitwala_ed/ui-spa/src/layouts/PortalLayout.vue`

**Implication**
- This drift was real and is now removed. The guardrail should keep it from being reintroduced silently during future edits.

### 5. Scoped CSS is not the main problem, but visual scoped CSS needs stricter rules

**Mostly safe layout-only examples**
- `ifitwala_ed/ui-spa/src/pages/staff/StaffHome.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/AttendanceAnalytics.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/schedule/student-groups/StudentGroups.vue`

**Riskier visual ownership examples**
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/AttendanceLedger.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/EnrollmentAnalytics.vue`
- `ifitwala_ed/ui-spa/src/pages/staff/analytics/StudentLogAnalytics.vue`

**Implication**
- The repo needs an explicit rule: page-local scoped CSS may own geometry and third-party behavior hooks, but not reusable visual identity.

---

## Priority Queue

### P0. Stop new drift

- Tighten `ifitwala_ed/ui-spa/AGENTS.md`
- Tighten `ifitwala_ed/docs/spa/02_style_note.md`
- Add an automated style guardrail with a legacy baseline

### P1. Completed in follow-up cleanup: remove undefined semantic names / vars

- normalize `mint`, `forest`, `warm-amber`, `ochre`, `coral`, `sun`, `muted`, `line-strong`
- normalize `--surface-soft-rgb`, `--slate-token-rgb`, `--bamboo`, `--footer-h`

### P2. Normalize shell families

- move `PortalLayout.vue` shell/background styling into canonical layout classes
- standardize route-root rules for staff, analytics, student/guardian, and admissions page families

### P3. Promote recurring visual patterns into shared primitives

- analytics filter panels and status pills
- portal alert/status surfaces
- schedule/student-group card treatments

### P4. Clean legacy CSS deliberately

- use `ifitwala_ed/ui-spa/src/styles/_style_audit_report.md` as a candidate list only
- delete legacy selectors only after runtime verification

---

## Recommended Ownership Model

- `tokens.css`: values only
- `app.css`: tiny global helpers only
- `layout.css`: route shells and structural containers only
- `components.css`: named reusable visual primitives only
- page `<style scoped>`: geometry, sticky behavior, responsive grid, third-party bridge code only
- templates: semantic classes first, raw palette utilities only for tightly local alert or data-viz needs

---

## Implemented In This Change

- documented this audit as a reference note
- tightened the authoritative SPA style guidance
- tightened local UI-agent instructions
- added automated SPA style guardrails and then cleared the baseline after removing the undefined semantic utilities and stray CSS vars
