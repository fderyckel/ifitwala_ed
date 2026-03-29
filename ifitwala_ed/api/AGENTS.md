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
- For governed file/image reads, return a server-owned display/open URL for private media instead of exposing raw private paths.

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
