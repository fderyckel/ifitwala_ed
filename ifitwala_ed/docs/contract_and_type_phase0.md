# contracts_and_types_governance_phase0.md

Status: **Phase 0 (now)** — governance + guardrails + first contracts
Scope: `ui-spa/src/{types,lib,utils}`, SPA ↔ server contracts, service transport, role-scoped DTOs

This document is written for **Codex agents + human reviewers**.
It converts our existing SPA rules into an enforceable contract system that scales without drift.

---

## 0) Why this exists

We already saw predictable drift:

* runtime constants/configs sneaking into `types/`
* duplicate “payload types” living inside Vue pages
* a parallel `fetch()` transport existing alongside `createResource`

At small scale this is tolerable.
At scale (more modules, analytics, agents), it becomes:

* silent contract mismatches
* accidental data exposure across surfaces
* fragmented caching/error handling
* expensive refactors later

**Phase 0 goal:** make contracts and types *enforceable*, not aspirational.

---

## 1) Non‑negotiable rules

### 1.1 `types/` = contracts only (zero runtime)

Hard rules:

* ✅ Allowed: `export type`, `export interface`, literal unions
* ❌ Forbidden: `export const`, `export function`, side effects, Vue imports

**Review rule:** if `types/` contains runtime code → FAIL.

---

### 1.2 `utils/` = pure stateless helpers

* deterministic helpers only
* no state, no registries, no orchestration

---

### 1.3 `lib/` = runtime + services + orchestration

* services calling server
* runtime configs / constants
* signals, orchestration

❌ Not allowed:

* business rules (server owns them)
* overlay closing (overlay owns it)

---

### 1.4 One transport only

* ❌ no `fetch()` (direct or wrapped)
* ✅ all server calls use `createResource`

---

## 2) What we mean by **Contracts** (core concept)

### 2.1 Plain definition

A **contract** is an explicit, named description of:

* what the client is allowed to send to the server
* what the server promises to return

Nothing more. Nothing less.

A contract is **not**:

* UI state
* business logic
* workflow rules

It is the *boundary agreement* between SPA and server.

---

### 2.2 Why types alone are not enough

Today, many payload types live:

* inside Vue pages
* inside services
* sometimes duplicated

That means the *real contract* exists only implicitly, in the server code.

Contracts make that boundary:

* visible
* reviewable
* enforceable

---

## 3) Contract files (Phase‑0 format)

Create:

```
ui-spa/src/types/contracts/
```

Structure by domain:

```
types/contracts/
  focus/
    list_focus_items.ts
    resolve_focus_item.ts
  student_log/
    submit_follow_up.ts
```

Each file exports **only types**.

---

## 4) Contract file structure

Example:

```
export type Request = {
  open_only: 0 | 1
  limit?: number
  offset?: number
}

export type Response = {
  items: FocusItemDTO[]
  total: number
}
```

Rules:

* matches server whitelisted method **exactly**
* no runtime code
* no defaults
* no inference

---

## 5) Role‑scoped DTOs (security by design)

If the same DocType is exposed differently:

* staff
* student
* guardian

Then define separate DTOs:

```
StudentLogStaffDTO
StudentLogStudentDTO
StudentLogGuardianDTO
```

Even if identical today.

This prevents accidental UI leakage.

---

## 6) Runtime enums & configs

Pattern:

* `types/` → literal unions only
* `lib/constants/` → runtime arrays/maps

Never colocate runtime data in `types/`.

---

## 7) Services and contracts

Services:

* live in `lib/services/`
* call `createResource`
* import contract types

Services do NOT:

* close overlays
* implement workflow rules

---

## 8) Enforcement (Phase‑0)

### CI / script checks

Fail build if:

* `types/` contains `export const`
* any file contains `fetch(`

### Review checklist

* new endpoint → new contract file
* no page‑local API payload types
* role‑scoped DTOs where relevant

---

## 9) Phase‑0 completion criteria

Done when:

* zero runtime code in `types/`
* zero `fetch()` usage
* Focus + Student Log endpoints have contracts
* at least one domain uses role‑scoped DTOs

---

## 10) Mental model

> **Server owns truth.**
> **Contracts name the truth.**
> **Types enforce the truth.**
> **Services obey the truth.**
> **UI renders the truth.**

End.
