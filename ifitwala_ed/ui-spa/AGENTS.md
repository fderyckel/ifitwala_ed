File: ifitwala_ed/ui-spa/AGENTS.md

# AGENTS.md — UI SPA Local Rules

This file adds local rules for work inside `ifitwala_ed/ui-spa/`.
The root `AGENTS.md` remains authoritative and must still be obeyed.

This folder owns the portal/app-like UX for staff, students, and guardians.
Agents working here must optimize first for product UX, then contract safety.

---

## 0. Local Mission

Inside `ui-spa`, prioritize:

1. lowest-friction user workflows
2. zero silent failures
3. strict client/server contract fidelity
4. minimal page-init latency
5. no UI drift from server-owned invariants

The SPA is a UX shell. It is not the source of truth.

## 0.1 Local Environment Note

- This Codex session runs on the user's local machine for this repository.
- Do not add generic closeout notes about missing `frappe`, missing `bench`, or shell `PATH` differences unless a specific command failed and the exact failure is necessary to explain what could not be verified.

---

## 1. UX Rules (Non-Negotiable)

- Actions must appear where users already work.
- Avoid forcing navigation when an overlay, inline action, or contextual workflow is better.
- Preserve user context:
  - selected school
  - filters
  - tab state
  - selected student/group/document
- Common workflows should minimize page-hopping and modal chaining.
- Any blocked action must explain:
  - what is wrong
  - what the user needs to do next

Silent no-op behavior is a defect.

---

## 2. Overlay / Modal Discipline

- Use the single approved overlay system only.
- Overlay responsibilities must remain strict.
- Overlays are not refresh owners.
- Overlays must not invent business logic.
- Overlays must support explicit entry-point modes when applicable:
  1. prefilled/locked context mode
  2. selection-required mode

If an overlay works from one entry point but fails from another, treat it as a design bug.

---

## 3. A+ SPA Contract Rules

- Do not normalize or “fix” bad backend contracts in components.
- Do not add ad-hoc transport normalization.
- Respect the canonical POST payload shape.
- Use explicit request/response contracts.
- Do not silently unwrap, reshape, or defend against arbitrary backend drift in the SPA.
- For governed/private media, consume only server-resolved display URLs; never construct or forward raw private file paths in components.

If the backend contract is wrong, fail clearly and fix the backend.

---

## 4. Routing Rules

- Never hardcode the SPA base prefix.
- Use named routes or base-less internal paths only.
- Do not use `window.location` for internal SPA navigation unless explicitly leaving the SPA.

Internal navigation must preserve the current application shell and state model.

---

## 5. Data-Loading Rules

- Avoid request waterfalls.
- Prefer one aggregated endpoint for tightly related page-init data.
- Use `Promise.all()` only for truly independent domains.
- No page should require more than 5 foundational API calls without strong justification.
- Treat dashboards, staff home, attendance, and analytics as hot paths.

When page-init data is repeated or expensive, ask whether it should be aggregated or cached server-side.

---

## 6. Error / Feedback Rules

- No silent action failure.
- Blocked actions must show inline errors and/or toast.
- UI feedback must be actionable.
- Never pretend success if server confirmation is missing.
- Never let UX masking hide a server-side invariant failure.

---

## 7. Watcher / Setup Safety

- Declare refs/computed before watchers that use them.
- Be careful with `immediate` watchers.
- Assume minified runtime errors may be TDZ/setup-order issues first.
- Keep debugging output inside callbacks, not watcher argument positions.

---

## 8. Styling Rules

- Follow Vue + Tailwind + frappe-ui direction only.
- Do not introduce Bootstrap patterns in touched code.
- Use semantic typography helpers and project styling rules.
- Respect root-owned typography and scoped styling discipline.
- Do not create cross-surface style leakage.
- Treat routed page-root shell/container classes as locked SPA contracts, not disposable local styling.
- Preserve canonical page wrappers such as `staff-shell` unless the shell contract is being intentionally redesigned and documented first.
- When rewriting a page, compare its root container against sibling routes in the same surface before finalizing layout changes.
- Do not swap a shared shell for ad-hoc root classes (`min-h-screen`, page-local padding, custom max-width) without updating the canonical SPA note in the same approved change.
- For every routed page change, identify the owning surface first:
  - staff workspace pages -> `staff-shell`
  - staff analytics pages -> `analytics-shell`
  - student / guardian pages -> layout-owned shell, page root usually `portal-page` or equivalent rhythm-only structure
  - admissions pages -> layout-owned shell, page root usually `admissions-page` or equivalent rhythm-only structure
- Reuse classes from `src/styles/components.css` and `src/styles/layout.css` before reaching for raw palette utilities.
- Native Tailwind palette colors are allowed only for tightly local alert states or charts; they must not define a page's overall visual language.
- Do not introduce undefined semantic utilities or CSS vars. If a new style semantic is truly needed, update `tokens.css`, `tailwind.config.js`, and `ifitwala_ed/docs/spa/02_style_note.md` in the same change.
- Page `<style scoped>` blocks may own layout geometry, sticky behavior, and third-party integration details. Reusable visual styling belongs in shared CSS files.
- Before finalizing any UI styling change, run `python3 scripts/spa_style_guardrails.py` or `bash scripts/contracts_guardrails.sh`.
- If a touched page already contains legacy drift, do not extend that drift casually. Either normalize it or leave it isolated and call it out.

---

## 9. Security & Visibility Reminder

The SPA must never be treated as a permission boundary.

- Client guards are UX only.
- Server owns correctness.
- Do not hide missing backend permission checks behind frontend conditions.
- Never expose more data than the surface needs.
- If a media asset fails due to permission or missing file access, show a fallback state and treat the API/display contract as the bug to fix, not the component.

---

## 10. Delivery Checklist for SPA Changes

Before finalizing a SPA change, verify:

- workflow got easier, not just prettier
- action placement is contextual
- no silent failures remain
- entry-point modes are explicit
- routing rules are preserved
- no hardcoded base prefixes were introduced
- no backend contract normalization was added
- data loading is not bloated or waterfall-heavy
- style guardrails still pass and no new semantic token drift was introduced
- related overlays/pages remain safe under repeat clicks and slow networks

---

## 11. High Concurrency SPA Rule

The canonical performance/concurrency note for SPA integration work is:

- `ifitwala_ed/docs/high_concurrency_contract.md`

For SPA surfaces, this means:

- one bounded bootstrap/read call per page mode wherever practical
- no client waterfalls for tightly related data
- explicit refresh ownership
- no accidental request stampedes from watchers, repeated mounts, or overlapping invalidations
- no background refresh loops without a bounded stale policy

If a page needs many dependent calls to become usable, stop and redesign the server contract first.

---

## 12. Drive Surface Rule

When integrating Ifitwala_drive into the SPA:

- treat Drive as the file authority
- keep Ifitwala_Ed as the context authority
- use typed contracts for Drive browse and grant APIs
- do not use raw `file_url` as the primary SPA contract
- use preview/download grants for file actions
- prefer route-based workspaces for sustained browsing and overlays only for short, focused mutations

Drive browsing pages must remain A+ compliant:

- typed request/response contracts
- no transport normalization
- bounded page-init requests
- no guessing of storage paths or URL formats in components
