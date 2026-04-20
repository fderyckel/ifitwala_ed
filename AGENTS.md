File: AGENTS.md

# AGENTS.md — Ifitwala_Ed Repository Constitution

This repository is a production-grade, multi-tenant Education ERP built on **Frappe Framework v16** with a **Vue 3 + Tailwind + frappe-ui SPA**.

This file is the **root constitution** for all agents working in this repository.
Nested `AGENTS.md` files may add local rules, but they must never weaken this contract.

---

## 0. Prime Directive (Non-Negotiable)

> **Do not invent. Do not assume. Do not drift.**

- Never invent field names, DocTypes, schemas, routes, payloads, permissions, defaults, or workflow rules.
- Never rely on memory of older repo versions.
- Always work from files currently present in the workspace.
- If required files, contracts, or schemas are missing: **STOP. ASK. WAIT.**

---

## 0.1 Execution Priority Order (Non-Negotiable)

When evaluating any change, think in this order:

1. Product UX
2. Security and permissions
3. Data integrity and workflow invariants
4. Multi-tenant isolation
5. High concurrency and scalability
6. Framework correctness
7. Code style and cleanup

If a change improves code elegance but weakens product UX, security, data integrity, or concurrency safety, reject it.

---

## 0.2 Product Mandate (Non-Negotiable)

Agents must operate with a product manager mindset and reduce friction for real users:

- teachers
- admissions staff
- academic staff
- guardians
- students
- administrators

Rules:

- Prefer in-product workflows over CLI/manual operator steps.
- Eliminate avoidable navigation and context switching.
- Surface actions where users already work.
- Silent UI dead ends are defects.
- Blocked actions must explain:
  - why the action is blocked
  - what the user should do next

Before implementing workflow/UI changes, ask:

- Is this the lowest-friction path?
- Is the next action obvious?
- Does the UI preserve user context?
- Is failure actionable instead of silent?

---

## 0.3 Framework Baseline (Non-Negotiable)

- Runtime baseline is **Frappe Framework v16**.
- Any workflow, setup, patch, or instruction that pins framework version must target **`version-16`**.
- For Frappe list/query pagination in Python, JS, and typed contracts, use `limit`, never `limit_page_length`.

---

## 0.4 Local Environment Communication Rule

- Codex is running on the user's local machine in this repository, not on a remote production server.
- Do not add boilerplate disclaimers that the repo `.venv` does not contain `frappe`, that `bench` is not on `PATH`, or that the current shell is not the server.
- If verification is blocked, report only the concrete blocker for the command you attempted and keep the note short.
- Do not treat local shell path differences as architecture insight or as a reason to add generic environment caveats to the closeout.

---

## 1. Operating Discipline

### 1.1 Mandatory Workflow

For non-trivial tasks, agents MUST:

1. Restate the task precisely.
2. Identify exact files to inspect and likely files to change.
3. Summarize relevant doc/code/contract constraints.
4. List key risks:
   - UX regressions
   - permission leaks
   - data integrity/workflow regressions
   - concurrency/performance regressions
5. Stop for explicit approval before:
   - structural refactors
   - schema changes
   - cross-module behavior changes
6. Execute only approved work.

No opportunistic cleanup. No scope creep.

### 1.2 Generated Artifact And I18n Discipline

- Do not commit or leave behind oversized generated audit artifacts, scan dumps, or machine-produced markdown unless the user explicitly asks for them to live in the repo.
- Before writing generated docs under `ifitwala_ed/docs/`, prefer concise human review outputs over exhaustive raw dumps.
- If a generated artifact is likely to be large, split it, summarize it, or keep it outside the tracked repo workflow.
- Treat any single generated markdown file approaching repository or tool limits as a process failure to avoid, not a lint issue to discover later.
- For i18n, translation functions must receive stable literal source strings only.
- Never pass variables directly to `_()` or `__()`.
- Never use f-strings, template literals, or string concatenation as the translatable source sentence.
- When dynamic data is required, use a literal source string with named placeholders, then format after translation.

---

## 2. Architectural Authority & Drift Control

- Architecture is explicitly locked.
- Markdown under `ifitwala_ed/docs/` is authoritative.
- Code and documentation must never silently diverge.
- If requested behavior changes:
  - identify the canonical doc
  - update docs together with code when approved

Drift is a bug.

### 2.1 Documentation Authority Protocol

- Documentation is the source of truth for behavior and architecture.
- If documentation is ambiguous, clarify documentation first, then align code.
- Agents MUST NOT change code in ways that alter documented behavior without:
  - pros
  - cons
  - blind spots
  - risks
  - explicit approval

### 2.1.1 Documentation Routing Protocol

When starting non-trivial work, find the canonical doc before designing or editing.

Read in this order:

1. nearest applicable `AGENTS.md`
2. `ifitwala_ed/docs/README.md`
3. the relevant docs-folder `README.md` when one exists
4. the feature's canonical contract doc(s)
5. cross-cutting contracts such as:
   - `ifitwala_ed/docs/high_concurrency_contract.md`
   - `ifitwala_ed/docs/nested_scope_contract.md`
   - `ifitwala_ed/docs/testing/01_test_strategy.md`

Routing rules:

- Prefer docs that explicitly say `Canonical`, `Active`, `Locked`, or that include concrete `Status`, `Code refs`, and `Test refs`.
- Treat `proposal`, `audit`, `history`, `phase`, and `notes` files as non-authoritative unless the file itself says it is the current canonical/runtime contract.
- Treat `ifitwala_ed/docs/docs_md/` as end-user and DocType-facing guidance, not as the default source for runtime architecture, unless a feature contract explicitly points there.
- If a folder has a `README.md`, use it as the navigation index rather than scanning file names and guessing authority.

For any change involving governed uploads, links vs files, private-media open/download URLs, picture thumbnails, image/PDF preview, or attachment DTOs, read these exact docs before editing:

1. `ifitwala_ed/docs/files_and_policies/README.md`
2. `ifitwala_ed/docs/files_and_policies/files_01_architecture_notes.md`
3. `ifitwala_ed/docs/files_and_policies/files_03_implementation.md`
4. `ifitwala_ed/docs/files_and_policies/files_07_education_file_semantics_and_cross_app_contract.md`
5. `ifitwala_ed/docs/files_and_policies/files_08_cross_portal_governed_attachment_preview_contract.md`
6. the relevant surface note such as `files_05_organization_media_governance.md`, `files_06_org_communication_attachment_contract.md`, or `docs/admission/03_portal_files_gdpr.md`
7. `../ifitwala_drive/ifitwala_drive/docs/06_api_contracts.md` when touching the Ed/Drive seam

If the surface is admissions-specific, also read:

- `ifitwala_ed/docs/admission/05_admission_portal.md`
- `ifitwala_ed/docs/admission/10_ifitwala_drive_portal_uploads.md`

### 2.2 Legacy Code Policy

During development:

- Do not introduce compatibility shims, duplicate flows, or fallback routes unless explicitly approved for runtime contract preservation.
- Remove obsolete or broken paths when approved.
- Keep one canonical workflow path per feature.

---

## 3. Doctype & Data Model Invariants

### 3.1 No Business Logic in Child Tables

- Child table controllers must be empty or UI-only.
- Validation, computation, side effects, and workflow logic belong in the parent DocType.

Logic in child controllers is a bug.

### 3.2 Schema Discipline

Agents MUST NOT invent field names.

- Never map/copy/read a field unless its existence is verified from authoritative schema.
- Never defensively read missing fields merely to avoid runtime errors.
- If a target requires data the source schema does not provide, stop and require an explicit architecture/schema decision.
- Never change DocType metadata `.json` or server-side production logic solely to make a test pass.
- If a test is failing because of setup, fixtures, naming, or isolation, fix the test or fixture first.
- Any DocType metadata `.json` change requires explicit user approval before editing.

Allowed sources:

- provided JSON schema files
- `frappe.get_meta()` only when appropriate and justified

If schema is incomplete or ambiguous: ask.

### 3.2.1 JSON Metadata Timestamp Discipline

When a Frappe metadata `.json` file is touched:

- update its `modified` timestamp to the real change date/time

A stale `modified` timestamp is a bug.

### 3.3 NestedSet Is Sacred

Any DocType using `NestedSet` (`lft`, `rgt`):

- must preserve hierarchy integrity
- must use framework helpers only
- must never be modified via manual SQL
- must treat create-time validation as a separate path: unsaved nodes do not have valid tree position yet
- must not call descendant / ancestor expansion helpers on a new document unless the helper explicitly supports unsaved nodes
- when validation depends on tree scope, branch on `is_new()` and validate against the pending node only or another explicitly safe create-time scope
- tree-backed validation changes must include regression coverage for both new-record save and existing-record update paths

---

## 4. Multi-Tenant Safety (Non-Negotiable)

This is a multi-tenant SaaS for schools. Assume sibling isolation is mandatory.

Every query and workflow must be explicitly evaluated for scope:

- organization
- school
- descendants / hierarchy
- program / academic year / term when relevant
- user role and relationship to the target record

Rules:

- Never write broad or implicit queries where tenant scope is merely assumed.
- Reuse canonical permission/scope helpers where they exist.
- Do not reimplement scope math ad hoc in each endpoint or UI surface.

---

## 5. Backend (Frappe) Engineering Rules

### 5.1 Controllers & Hooks

- Prefer Document controllers:
  - `before_insert`
  - `before_save`
  - `after_insert`
  - `on_update`
  - `on_submit`
- Avoid hooks unless unavoidable.
- Child table controllers remain empty.

### 5.2 Database Discipline

- Reduce DB round-trips.
- Prefer:
  - `frappe.db.get_value`
  - `frappe.db.get_values`
  - `frappe.get_all`
- Query Builder
- parameterized SQL
- Never interpolate SQL strings manually.
- Never use broad queries when indexed scoped queries are available.

### 5.2.1 Read-Plan Discipline For Hot Paths

When touching dashboards, reports, page-init endpoints, or other hot read surfaces:

- identify every helper the endpoint calls and what each helper reads
- collapse duplicated stable reads into one shared preload context when multiple blocks need the same inputs
- do not accept "same data, different helper" as a reason to reread the database
- when replacing per-row `get_doc(...)` work with preloaded rows, verify the downstream helper's full field contract first
- batched/preloaded substitutes must include every field later used by validation, equality, sorting, permissions, and derived state
- add targeted tests that fail if the hot path falls back to per-row `get_doc(...)`, `frappe.db.get_value(...)`, or equivalent repeated reads

---

## 5.3 High Concurrency Contract (Non-Negotiable)

The canonical repo-wide concurrency and caching note is:

- `ifitwala_ed/docs/high_concurrency_contract.md`

Agents must treat that note as binding for:

- request sizing
- cache ownership and invalidation
- async vs synchronous boundaries
- nested-scope reuse
- refresh fan-out control
- read-model vs mutation-path separation

When implementing new surfaces, especially SPA surfaces and file-heavy workflows:

- prefer one bounded bootstrap/read endpoint over request waterfalls
- do not move correctness-critical work to async just to hide latency
- do not add client-driven polling or refresh loops without explicit ownership
- do not introduce cache layers without invalidation ownership

If a change conflicts with `high_concurrency_contract.md`, that note wins.

---

## 5.4 Ifitwala Drive Integration Rule

Ifitwala_drive is the governed file authority.

When Ifitwala_Ed integrates file browsing, upload, preview, or download:

- do not guess raw file URLs
- do not treat storage paths as product truth
- do not recreate file governance inside Ifitwala_Ed
- use Drive APIs and canonical references as the integration boundary
- keep Ifitwala_Ed context-first and Drive as the file authority

SPA and backend work must preserve:

- context-first retrieval
- bounded request counts
- permission-safe file access
- reuse of Drive browse and grant APIs instead of duplicate file transport logic
- surface-specific visibility contracts for governed file/image reads
- server-resolved display/open URLs for private media instead of raw private paths

## 5.4.1 Async Queue Boundary Rule

When Ed code relies on Drive or any async follow-up work:

- internal queue labels are not automatically valid Frappe runtime queues
- any `frappe.enqueue(...)` queue must either be a standard queue (`short`, `default`, `long`), a documented custom runtime queue, or be normalized to a runtime-valid queue at the enqueue boundary
- user-visible mutation success must not be lost merely because deferred enrichment selected an undeployed semantic queue label
- if a change adds or renames queue labels, update the canonical docs/runbook in the same change and add regression coverage for the enqueue boundary

### 5.3 Caching Rules

Shared or stable data should use Redis-backed caching where safe:

- `frappe.cache()`
- `frappe.get_cached_value`
- `frappe.get_cached_doc`
- approved Redis-backed cache helpers

Never cache:

- permission-sensitive queries without scoped keys
- user-specific state unless explicitly designed for it

Cache keys must include relevant scope:

- user
- school
- organization
- filters

Stale cache without an invalidation strategy is a bug.

For every new shared cache, agents must define and verify:

- exact key shape
- scope dimensions
- owner invalidator function
- dependent caches/helpers that must also be invalidated
- mutation hooks that trigger invalidation

Rules:

- do not replace request-local dict caches on hot paths with Redis caches unless invalidation ownership is explicit
- do not stop at the cache you added; also clear dependent helper caches such as ancestor-chain or effective-resolution caches
- avoid prefix-wide or global cache wipes as the default invalidation strategy in multi-tenant domains
- if broad invalidation is temporarily unavoidable, call it out explicitly as a concession and say what narrower ownership is still missing
- cache changes must include tests for both reuse and invalidation

---

## 6. High-Concurrency Mandate (Non-Negotiable)

Assume peak load by default.

Design for staff, students, and guardians using the system concurrently.

### 6.1 Request Path Rules

Request handlers must stay short.

Heavy or repeated work must leave the request path via Frappe-native primitives.

Prefer:

- `frappe.enqueue(...)` with explicit queue selection
- short/default/long queue separation
- bounded batch processing
- realtime completion with `frappe.publish_realtime(...)` where useful
- aggregated page-init endpoints instead of request waterfalls
- explicit invalidation rules for cached payloads

Avoid:

- synchronous loops over many records in request handlers
- N+1 queries
- repeated `get_doc(...)` in loops for dashboards or list payloads
- per-row email/network side effects in requests
- unbounded scheduler sweeps
- oversized transactions

When an endpoint returns multiple blocks or panels:

- write down which inputs are shared across blocks
- preload shared stable inputs once
- pass the shared inputs through explicitly instead of letting each block query independently
- keep permissions and tenant scoping enforced before preload fan-out, not after payload assembly

### 6.2 Scheduler & Job Rules

Background jobs and scheduled jobs must be:

- idempotent
- chunked
- observable
- safe under overlap/retry

Schedulers should dispatch work, not do giant processing inline.

### 6.3 Hot Path Rule

When touching:

- analytics
- dashboards
- attendance
- enrollment
- reporting
- scheduler work
- staff cockpits

assume it is or will become a hot path.

Optimize:

- query count
- payload size
- cacheability
- batching
- idempotency

Hot-path write changes must also follow these rules:

- if you skip `save()` for unchanged rows, verify the target controller/hooks do not provide required side effects for that path
- compare equality against the full payload the controller cares about, not a partial subset
- add regression coverage for the no-op path and the changed path

---

## 7. Time, Calendar & Scheduling Rules

- Always use the Frappe site timezone.
- Never use server OS timezone.
- Never hardcode country timezones.

Helpers dealing with time must support:

- `datetime.timedelta`
- `datetime.time`
- `datetime.datetime`
- `str`

Rules:

- centralize coercion/parsing
- no ad-hoc parsing
- no silent failures
- missing resolution must emit structured debug information

---

## 8. Frontend Architecture (Locked)

### 8.1 Canonical Frontend Direction

- Vue 3
- Tailwind CSS v4
- frappe-ui

Build pipeline expectations:

- root `yarn build`
- `bench build`
- unified Desk Rollup + `ui-spa` Vite compilation

Bootstrap is deprecated legacy and must not be extended in touched code.

### 8.2 SPA Interaction & API Contract Invariants

- No silent user-action failures.
- Blocked actions must show inline error and/or toast.
- POST payload shape must match server contract exactly.
- Do not wrap payloads incorrectly.
- Avoid setup-order / immediate-watch TDZ bugs.
- Multi-entry overlays must explicitly support:
  - prefilled/locked mode
  - selection-required mode
- Use named routes or base-less internal paths only.
- Do not hardcode SPA base prefixes.

### 8.3 SPA Shell Container Discipline

- Shared routed-page shell/container classes are architecture, not optional styling.
- When touching routed SPA pages, preserve the canonical page-root shell for that surface (for example `staff-shell` on staff pages) unless the shell contract is explicitly documented and approved to change.
- Do not replace a shared shell/container with ad-hoc root classes (`min-h-screen`, local padding, local max-width) during page rewrites just because the page still "looks acceptable" in isolation.
- Validate routed-page layout changes against sibling pages in the same surface, not only the touched page by itself.
- If a shell/container contract must change, update the authoritative SPA docs in the same approved change before editing affected page roots.

---

## 9. API / Workflow Design

Prefer domain-specific endpoints over generic CRUD assembly.

If an action has business meaning, it deserves:

- a named endpoint
- a single transactional path where possible
- server-side idempotency / uniqueness invariants
- explicit permission enforcement
- predictable response contracts

Page initialization should prefer one aggregated endpoint for tightly related data.
Use `Promise.all()` only for truly independent domains.

---

## 10. Permissions, Visibility & Hierarchy

- Schools belong to Organizations (NestedSet).
- Selecting a parent includes all descendants.
- Sibling isolation is mandatory.

Visibility rules must be enforced server-side.

Examples of locked rules:

- instructors see only students they teach
- logs visible only to author / assigned follow-up / explicitly privileged roles
- students and guardians never use Desk

Never swallow framework exceptions in permission or visibility logic.

---

## 11. Files & Media Handling

- Always use rename/move patterns safely.
- Avoid orphaned files.
- Respect:
  - `attached_to_doctype`
  - `attached_to_name`
  - folder case-sensitivity
- Sync linked User/Contact images when required.

### 11.1 File Governance

- Dispatcher-only creation via governed file APIs
- Classification required
- Atomic routing only
- No URL guessing in the UI
- No raw private file URLs in SPA/API display contracts
- Governed private-media read routes must never emit raw `/private/...` redirect targets; they must stream inline content or redirect only to a server-owned/public/external URL explicitly allowed by the surface contract
- Each governed read surface must define who may open the resolved display URL
- Any change to governed file/image visibility must update permission tests in the same change
- Deterministic derivative slots
- Docs under `ifitwala_ed/docs/files_and_policies/` are authoritative

---

## 12. Analytics & Reporting Rules

- Guard permissions early
- Build WHERE clauses centrally
- Prefer one indexed query over many
- Strip HTML in summaries, not print views
- Display time as `hh:mm`
- Sort by real datetime, not formatted strings

---

## 13. Error Handling & Debug Protocol

- Silent failures are forbidden.
- If core context exists but resolution fails:
  - emit structured debug payload
  - log relevant Python types when useful
- Never return `None` without explanation

Client guards are UX only.
Server invariants own correctness.

---

## 14. Documentation Synchronization

When architecture or behavior changes are approved, update corresponding docs.

For markdown under `ifitwala_ed/docs/docs_md/`:

- every doc must include YAML:
  - `version`
  - `last_change_date`
- any doc change must update both fields
- `## Technical Notes (IT)` must remain the final top-level section
- preserve figure tags exactly

---

## 15. Testing & Validation Checklist

Before considering work done, verify:

- documented behavior is preserved or intentionally updated
- server invariants are enforced
- permissions are enforced server-side
- tenant scope is respected
- UI does not fail silently
- change is safe under concurrency
- caches/jobs/idempotency are used where needed
- governed file/image display URLs match the intended surface visibility contract
- permission-matrix tests cover any changed governed file/image read route
- related tests are added or updated when required

If a critical assumption cannot be verified from the workspace, stop and say exactly what is missing.

### 15.1 Test Isolation Rules

- Test modules must be import-safe under Frappe test discovery.
- Never mutate `sys.modules`, `frappe.db`, `frappe.session`, or other framework globals at module scope in `test_*.py`.
- Never install fake modules or global stubs during test-module import.
- Scope stubs/monkeypatches inside the test, fixture, or context manager and restore them automatically.
- A test that passes in isolation but contaminates later imports or framework cleanup is broken.

---

## 16. Frappe Security Model (Learned)

When assessing security in Frappe Framework code, understand the framework's built-in protections before claiming vulnerabilities.

### 16.1 SQL Escape Behavior

`frappe.db.escape()` returns **quoted, escaped literals** — not raw strings.

```python
# escape("O'Brien") → 'O\'Brien'  (quotes included in output)
# This makes f-string concatenation with escaped values SAFE from injection
```

**Rule**: Code using `frappe.db.escape()` in SQL construction is protected against injection, even if stylistically questionable. Distinguish between "code smell" and "exploitable vulnerability."

### 16.2 HTML Sanitization Stack

Frappe uses **Bleach** internally for HTML sanitization:

```python
from frappe.utils import sanitize_html  # Bleach-based

# Strips: <script>, event handlers (onclick, onerror), javascript: URLs, dangerous data URIs
```

When auditing for XSS:
1. **Always trace the complete data flow** — user input → storage → API → UI
2. **Check controller hooks** (`before_insert`, `before_save`, `validate`) for existing sanitization
3. **Verify the sanitization is actually applied** — don't assume absence based on API response

**Example pattern that IS safe:**
```python
class PolicyVersion(Document):
    def before_insert(self):
        self._sanitize_policy_text()  # Called here

    def before_save(self):
        self._sanitize_policy_text()  # And here

    def _sanitize_policy_text(self):
        from ifitwala_ed.utilities.html_sanitizer import sanitize_html
        self.policy_text = sanitize_html(self.policy_text or "")
```

Even though `policy_text` flows to `v-html` in Vue, it's sanitized at the controller level.

### 16.3 Data Flow Verification Required

Before claiming XSS:
- Verify raw user input reaches the database unsanitized
- Verify the API returns unsanitized content
- Verify the UI renders without sanitization

**All three must be true for stored XSS to exist.**

### 16.4 Server-Generated Safe HTML

Content generated server-side with `html.escape()` is safe for `v-html`:

```python
def generate_diff_html(old, new):
    return f"<div>{escape(old)} → {escape(new)}</div>"  # Safe
```

The `html.escape()` function encodes `<`, `>`, `&`, and `"` — making injection impossible.

### 16.5 Framework-Aware Assessment

**DON'T**: See `v-html` in Vue + user input field → claim XSS
**DO**: Trace: User input → Controller hook sanitization? → API response → Vue rendering

What looks vulnerable in raw web frameworks may be **protected by Frappe's multi-layer defenses**:
- DocType controller hooks
- Permission system
- Built-in sanitizers
- Query parameterization

### 16.6 Testing Security Claims

Before reporting a security issue:
1. Create a reproduction attempt with actual payloads
2. Verify the payload executes (for XSS) or the query structure changes (for SQLi)
3. If protected by framework behavior, document it as "defense in depth" not "critical vulnerability"

**Reference**: See `ifitwala_ed/utilities/html_sanitizer.py` for project-specific sanitization wrappers.

---

## 17. Final Safety Rule

If unsure:

- pause
- ask
- wait

> A correct pause beats a confident regression.
