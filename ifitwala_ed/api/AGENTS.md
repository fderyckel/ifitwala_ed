File: ifitwala_ed/api/AGENTS.md

# AGENTS.md — API Local Rules

This file adds local rules for work inside `ifitwala_ed/api/`.
The root `AGENTS.md` remains authoritative and must still be obeyed.

This folder owns server-facing contracts, workflow endpoints, and high-concurrency request design.

---

## 0. Local Mission

Inside `ifitwala_ed/api/`, prioritize:

1. explicit business endpoints
2. server-owned invariants
3. strict permission enforcement
4. multi-tenant scope safety
5. high-concurrency-safe request design

API endpoints are not generic transport wrappers.
They are contract surfaces for real workflows.

## 0.1 Local Environment Note

- This Codex session runs on the user's local machine for this repo.
- Do not add stock explanations about missing `frappe` in `.venv`, missing `bench` on `PATH`, or the shell not being the remote server unless a specific attempted command is blocked and that exact blocker matters.

## 0.2 Documentation Routing Protocol

Before changing API behavior, read the canonical docs in this order:

1. `ifitwala_ed/docs/README.md`
2. the relevant docs-folder `README.md` when one exists
3. the feature's canonical runtime contract

Always check these cross-cutting notes when relevant:

- `ifitwala_ed/docs/high_concurrency_contract.md` for hot paths, dashboards, bootstrap endpoints, caching, and async boundaries
- `ifitwala_ed/docs/nested_scope_contract.md` for hierarchy-aware scope, descendant inclusion, or location/school visibility
- `ifitwala_ed/docs/files_and_policies/README.md` for governed file/image routes
- `ifitwala_ed/docs/files_and_policies/files_08_cross_portal_governed_attachment_preview_contract.md` for stable `open_url` / `preview_url` / `thumbnail_url` DTO rules
- `ifitwala_ed/docs/testing/README.md` and `ifitwala_ed/docs/testing/01_test_strategy.md` before deciding test scope

If the API change touches uploads, attachment links, previews, thumbnails, or private-media routing, also read:

- `ifitwala_ed/docs/files_and_policies/files_01_architecture_notes.md`
- `ifitwala_ed/docs/files_and_policies/files_03_implementation.md`
- `ifitwala_ed/docs/files_and_policies/files_07_education_file_semantics_and_cross_app_contract.md`
- `ifitwala_ed/docs/admission/05_admission_portal.md` when the surface is admissions/applicant-facing or staff admissions review
- `ifitwala_ed/docs/admission/10_ifitwala_drive_portal_uploads.md` when the change touches admissions uploads or applicant images
- `../ifitwala_drive/ifitwala_drive/docs/06_api_contracts.md`

Treat proposal, audit, history, and implementation-companion notes as non-authoritative unless they explicitly declare themselves the current runtime contract.

---

## 1. Endpoint Design Rules

Prefer domain-specific workflow endpoints over CRUD assembly.

If an action has meaning, it deserves:

- a named endpoint
- explicit inputs
- explicit permission checks
- explicit invariants
- predictable response shape

Examples of meaningful actions:

- submit
- decide
- follow up
- reassign
- close
- reopen
- promote
- generate
- sync
- dispatch

Do not let the client assemble important workflows out of generic document mutations.

---

## 2. Contract Rules

- Respect the canonical flat payload convention where applicable.
- Do not invent payload wrappers.
- Do not widen response shape without cause.
- Do not silently change endpoint contracts.
- Keep request and response structures explicit and auditable.
- In Python API modules, `_()` is reserved for translation literals only; never assign to `_`, use `_` as a throwaway variable, or shadow the Frappe translation alias.
- For governed file/image reads, return a server-owned display/open URL for private media instead of exposing raw private paths.
- A governed private-media route must never set `frappe.local.response["location"]` to a raw `/private/...` path; if no safe redirect target exists, stream the file inline from the API route instead.
- Shared file-delivery helpers must return only a safe redirect target or `None`; route handlers own the final inline/private-media fallback behavior.

If contract behavior changes, docs must be updated with code.

---

## 3. Permission & Scope Rules (Non-Negotiable)

Every endpoint must be reviewed for:

- privilege escalation
- cross-school leakage
- cross-organization leakage
- ID enumeration / direct object reference risks
- alternate API surface bypass
- mixed-role precedence bugs

Rules:

- all visibility and permissions must be enforced server-side
- do not trust client hints for scope
- reuse canonical permission/scope helpers where they exist
- do not reimplement scope logic ad hoc per endpoint
- if a governed file/image route is surface-specific, document the allowed viewers explicitly and add/update a permission matrix test for that route

If staff/family/applicant roles may coexist, precedence must be explicit.

---

## 4. Concurrency & Request-Path Rules

Request handlers must stay short.

If work is heavy, repeated, fan-out, or slow, move it off the request path using Frappe-native primitives.

Prefer:

- `frappe.enqueue(...)`
- explicit queues
- bounded chunking
- idempotency guards
- realtime completion events where useful
- short TTL scoped cache for expensive reads

Avoid:

- long synchronous loops in request handlers
- repeated `get_doc(...)` in loops
- per-record side effects inline
- unbounded report generation in HTTP request cycles
- giant scheduler sweeps

When in doubt, assume the endpoint may become a hot path.

---

## 5. Query Rules

- Reduce DB round-trips aggressively.
- Prefer indexed, scoped queries.
- N+1 patterns are defects.
- Avoid repeated row-by-row lookup patterns for dashboards and list payloads.
- Batch by concern and assemble in memory when needed.

Every filtered column must be verified against authoritative schema.

Do not invent filters or “active flags” on child tables without proof.

---

## 6. Cache Rules

Use Redis-backed caching only where safe.

Cache keys must include all relevant scope:

- user
- role/visibility scope
- school
- organization
- filter parameters

Never cache unsafe broad payloads.
Never cache without an invalidation strategy.

Stale cache that can leak scope or misstate operational state is a bug.

---

## 7. Job / Scheduler Rules

For queued jobs and scheduler work:

- jobs must be idempotent
- large sets must be chunked
- failures must be isolated
- execution must be observable
- overlap/replay risk must be considered
- semantic queue labels are not enough by themselves; every `frappe.enqueue(...)` call must target a runtime-valid queue or normalize to one at the enqueue boundary
- if a mutation endpoint enqueues post-finalize or post-save work, missing custom worker topology must not become a browser-visible failure unless the workflow contract explicitly says the mutation is blocked

Schedulers should dispatch chunks, not process giant workloads inline.

---

## 8. Data Integrity Rules

Server invariants own correctness.

Client-side guards are UX only.

Rules that must be enforced here when relevant:

- uniqueness
- idempotency
- legal state transitions
- immutable/locked states
- duplicate click protection
- replay protection

Do not rely on the UI to protect workflow correctness.

---

## 9. Endpoint Delivery Checklist

Before finalizing an API change, verify:

- endpoint is domain-specific if workflow meaning exists
- permission checks are explicit and server-side
- scope is tenant-safe
- query count is controlled
- heavy work is queued if needed
- idempotency/duplicate protection exists where needed
- response shape remains stable or intentionally updated
- docs/contracts are updated if behavior changed
- related tests were added or updated where required

---

## 10. API Test Fixture Rules

- API tests must prefer supported fixture controls over monkeypatching framework internals.
- Do not patch `User.send_password_notification`, `User.send_welcome_mail_to_user`, `frappe.sendmail`, or `Document.run_notifications` just to keep fixture creation alive when a supported document flag or deterministic fixture state can prevent the side effect.
- If an API test must suppress a side effect, do it with the narrowest fixture-scoped data change possible and restore the original state in teardown.
