# Ifitwala Ed I18n And Translation Workflow

Status: Canonical workflow contract
Code refs:

- `ifitwala_ed/ui-spa/src/lib/i18n.ts`
- `ifitwala_ed/ui-spa/src/lib/datetime.ts`
- `ifitwala_ed/hooks.py`
- `scripts/i18n/audit.py`
- `scripts/i18n/check.sh`
- `ifitwala_ed/docs/audit/i18n_phase_02a_batch_plan.md`
- `ifitwala_ed/docs/audit/i18n_phase_02a_normalization_decisions.md`

Test refs: None yet
Last updated: 2026-04-26

This document locks the translation workflow before bulk translation starts.

The product goal is to translate Ifitwala Ed into:

- Arabic: `ar`
- German: `de`
- French: `fr`
- Thai: `th`

## 1. Current Runtime Status

Current runtime: partial i18n readiness.

Implemented:

- Python backend code already uses many `_()` translation wrappers.
- Desk/classic JavaScript already uses many `__()` translation wrappers.
- The Vue SPA has a runtime bridge at `ifitwala_ed/ui-spa/src/lib/i18n.ts`.
- SPA date formatting has a shared helper at `ifitwala_ed/ui-spa/src/lib/datetime.ts`.
- A repo-owned source audit script exists at `scripts/i18n/audit.py`.
- A repo-owned critical i18n guardrail exists at `scripts/i18n/check.sh` and runs in CI.
- Previous audit follow-up docs exist under `ifitwala_ed/docs/audit/`.

Not implemented:

- No tracked `ifitwala_ed/locale/main.pot`.
- No tracked `ifitwala_ed/locale/ar.po`.
- No tracked `ifitwala_ed/locale/de.po`.
- No tracked `ifitwala_ed/locale/fr.po`.
- No tracked `ifitwala_ed/locale/th.po`.
- No repo-owned PO validation script.
- No repo-owned translation automation script.
- No complete CI guardrail for PO placeholder/tag validation.
- No complete Arabic RTL validation path.

Decision: bulk translation must not start until the source audit and catalog pipeline are reproducible.

## 2. Translation Scope

The first translation program covers user-facing product surfaces:

- Frappe DocType metadata labels, descriptions, options, workspace labels, report labels, and print labels.
- Python backend validation, permission, workflow, and product-facing response messages.
- Desk/classic JavaScript labels, dialogs, alerts, buttons, and visible errors.
- Vue SPA portal/staff/admissions/student/guardian UI copy.
- Website templates, public admissions pages, reports, and print-format UI copy.
- Shared date/time/number display helpers where visible to users.

The translation program does not translate these by default:

- User-entered school content.
- Tenant-specific names such as schools, organizations, courses, staff, students, guardians, groups, and events.
- Stored policy text, communications, comments, notes, reflections, submissions, or assessment feedback authored by users.
- Internal debug labels, developer-only diagnostics, migration messages, and test-only strings unless they are shown to product users.
- End-user documentation under `ifitwala_ed/docs/docs_md/` unless separately approved.

If a string is ambiguous, classify it in the audit as `review_needed` instead of wrapping or translating it blindly.

## 3. Source String Rules

All source strings must follow the root `AGENTS.md` i18n discipline.

Required:

- Translation functions receive stable literal source strings only.
- `_()` and `__()` are reserved for translation only.
- Dynamic values use placeholders, then format after translation.
- Python should use named placeholders for product-facing dynamic messages.
- Vue/TypeScript should use the SPA `__()` helper and positional arguments until a richer contract is approved.

Forbidden:

- Assigning to `_` or `__`.
- Using `_` as a throwaway variable.
- Passing variables directly to `_()` or `__()`.
- Passing f-strings, template literals, or concatenated strings as translation sources.
- Using `__('...').replace(...)` or equivalent post-translation string surgery.
- Adding raw user-facing framework messages such as `frappe.throw("...")`.
- Translating parameter names or payload keys into user copy without product review.

### 3.1 Labels Versus Contract Values

Translation must never change a value that the system stores, compares, filters, routes, or sends through an API.

Keep these values canonical and untranslated:

- DocType names and document names.
- Fieldnames, route names, method names, payload keys, and permission role names.
- `docstatus` values and any value used in server-side workflow logic.
- Filter values such as `status,=,Open` or `voucher_type,=,Journal Entry`.
- Link field values, dynamic reference names, tenant names, and user-entered names.

When the same concept needs both a machine value and visible text, split the variables explicitly:

- `statusValue`, `doctypeValue`, `roleValue`, or equivalent for canonical values.
- `statusLabel`, `buttonLabel`, or equivalent for display-only labels.

Only display-only labels may be translated, and their source must still be a stable literal string. If a variable might also be a contract value, do not translate it; show the raw value or defer it for product review.

## 4. Glossary Policy

The glossary is a product contract, not a translator preference file.

Glossary entries must be maintained before translation batches start for these ERP nouns:

- Organization
- School
- Academic Year
- Term
- Program
- Program Offering
- Student Group
- Student
- Guardian
- Instructor
- Employee
- Applicant
- Inquiry
- Application
- Enrollment
- Attendance
- Assessment
- Task
- Submission
- Feedback
- Policy
- Consent
- Portfolio
- Class Hub
- Staff Home

Rules:

- Workflow status terms must stay aligned with the owning workflow contract.
- Do not merge distinct workflow verbs such as save, submit, approve, acknowledge, publish, archive, complete, cancel, and reject.
- Product nouns may be translated per locale only after glossary approval.
- Uncertain glossary terms stay untranslated or fuzzy until reviewed.

## 5. Locale Requirements

Arabic:

- Arabic requires RTL support.
- The SPA must set or inherit the correct text direction for Arabic views.
- Layout QA must include dense tables, overlays, dashboards, forms, and navigation.
- Icons that imply direction must be reviewed.

German:

- German requires text-expansion QA.
- Buttons, table headers, filters, and cards must tolerate longer translated strings.

French:

- French requires text-expansion and punctuation QA.
- Form labels and action copy must preserve workflow meaning.

Thai:

- Thai requires line-wrapping QA.
- Date formatting must not accidentally force English or Buddhist/Gregorian behavior inconsistently across surfaces.

All locales:

- Placeholders must match source strings exactly.
- HTML tags and Markdown links must be preserved exactly where present.
- Date, time, and number formatting must use centralized helpers where practical.

## 6. Required Automation Phases

### Phase 1: Reproducible Audit

Create a repo-owned audit script that classifies source strings by surface and risk.

Command:

- `python3 scripts/i18n/audit.py`

Critical guardrail command:

- `bash scripts/i18n/check.sh`

Expected output path:

- `.i18n-audit/current.json`

The output is generated audit data, is ignored by git, and must not be committed unless explicitly requested.

The audit must classify:

- `safe_mechanical`
- `interpolation_risk`
- `normalization_first`
- `review_needed`
- `non_user_facing`

### Phase 2: Source Cleanup

Use the audit output to clean source strings in batches.

Batch order:

1. Python backend safe strings.
2. Python interpolation-risk fixes.
3. Desk/classic JavaScript.
4. One Vue pilot surface.
5. Remaining Vue surfaces.
6. Templates, website pages, reports, and print formats.

### Phase 3: Frappe Catalog Pipeline

Create and maintain the Frappe v16 gettext catalog layer.

Required tracked files after this phase:

- `ifitwala_ed/locale/main.pot`
- `ifitwala_ed/locale/ar.po`
- `ifitwala_ed/locale/de.po`
- `ifitwala_ed/locale/fr.po`
- `ifitwala_ed/locale/th.po`

Required Frappe commands must be wrapped by repo-owned scripts:

- generate POT
- create missing PO files
- update PO files from POT
- compile PO files to MO files

### Phase 4: Translation Automation

Create a script that translates PO entries without overwriting reviewed translations by default.

Required behavior:

- preserve placeholders
- preserve tags
- preserve translator comments
- respect glossary terms
- mark uncertain translations as fuzzy
- support small batches
- support dry-run mode

### Phase 5: Locale And RTL Hardening

Centralize visible locale behavior and validate Arabic RTL.

Required surfaces for Arabic smoke testing:

- Staff Home
- Guardian Home
- Admissions Portal
- one dense analytics/dashboard page
- one modal or overlay workflow

### Phase 6: CI Guardrails

Add validation to the contract guardrail path.

Implemented:

- `bash scripts/i18n/check.sh` runs `scripts/i18n/audit.py --fail-on-critical`.
- `.github/workflows/ci.yml` runs the i18n guardrail in the `lint` job.

The guardrail must fail on critical i18n defects:

- invalid placeholders
- invalid tags
- nonliteral translation calls
- `_` or `__` reassignment in runtime code
- raw user-facing framework messages
- empty required translation entries when a release gate requires completion

### Phase 7: Pilot Translation

Translate one high-value surface in all four locales and run the full pipeline.

Recommended pilot:

- Admissions Portal, because it is external-facing, workflow-heavy, and includes family-facing copy.

### Phase 8: Bulk Translation

Translate by product surface, not by file extension.

Recommended order:

1. Navigation, login, permissions, and core error states.
2. Admissions.
3. Guardian and student portals.
4. Staff Home and dashboards.
5. Scheduling and attendance.
6. Assessment and gradebook.
7. Accounting, HR, admin, and setup.
8. Website/templates.
9. Reports and print formats.

## 7. Coding Agent Workflow

For translation-related work, agents must:

1. Read this file.
2. Read the nearest `AGENTS.md`.
3. Read the relevant feature contract for the touched surface.
4. Run or update the repo-owned audit once Phase 1 exists.
5. Keep changes surface-scoped and batch-scoped.
6. Avoid opportunistic copy rewrites outside the approved batch.
7. Report remaining `review_needed` findings explicitly.

Agents must stop and ask before:

- changing DocType metadata solely for translation convenience
- renaming workflow statuses
- changing product nouns
- changing route names
- changing runtime language-selection behavior
- adding a new translation storage mechanism outside Frappe gettext

## 8. Readiness Gates

Bulk translation may start only when:

- the audit script exists and produces stable current-state output
- critical source-string violations are either fixed or explicitly deferred
- the Frappe catalog pipeline exists
- the four target PO files exist
- placeholder/tag validation exists
- glossary terms are approved for all four locales or marked as unresolved
- Arabic RTL smoke criteria are defined

Release readiness for a locale requires:

- PO files compile successfully
- no critical placeholder or tag mismatch
- no unexpected fuzzy entries in release-gated surfaces
- `yarn build` succeeds
- SPA type-check succeeds
- selected smoke surfaces render acceptably for the locale

## 9. Open Questions

These require product review before bulk translation:

- Should end-user docs under `ifitwala_ed/docs/docs_md/` be translated in this program or treated as a later documentation-localization project?
- Which terms should remain in English for brand/product consistency?
- Should school tenants be able to override translated product copy per tenant?
- What review workflow will mark machine-generated PO entries as human-approved?
