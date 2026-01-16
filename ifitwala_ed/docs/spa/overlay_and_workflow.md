# Overlay & Workflow Lifecycle Contract — A+ Model

> **Status:** Canonical (subordinate only to Vue SPA Development Rules)
> **Scope:** All workflow‑triggering overlays

---

## 0. Authority

This document is **binding** for any overlay that triggers a user action.

If a workflow overlay violates this contract, it is a defect.

---

## 1. Core Decision (A+)

> **Overlay owns closing. UI Services own orchestration.**

Overlay closure must be:

* local
* immediate
* deterministic

Never gated by refresh, toast, or reload.

---

## 2. Ownership Matrix

| Concern        | Owner       |
| -------------- | ----------- |
| API calls      | UI Services |
| Business logic | Server      |
| Invalidation   | UI Services |
| Toasts         | UI Services |
| Overlay close  | Overlay     |
| Lifecycle      | OverlayHost |

---

## 3. Mandatory Overlay API

Inputs:

```ts
open: boolean
zIndex?: number
overlayId?: string
```

Outputs:

```ts
emit('close')
emit('after-leave')
emit('done', payload?)
```

---

## 4. Success Sequence (Locked)

On success:

1. emit `close`
2. optionally emit `done`
3. return control to OverlayHost

Anything else is best‑effort.

---

## 5. UI Services Contract

UI Services:

* call endpoints
* normalize responses
* emit invalidation signals

UI Services **never**:

* close overlays
* mutate overlay stack

---

## 6. Naming Rules

Forbidden:

* get_context
* resolve_context

Approved:

* resolveFocusItemPayload
* listFocusItems
* submitFollowUp

Naming ambiguity must be resolved immediately.

---

## 7. Subsumed Notes

This document **subsumes**:

* overlay_contract_governance.md
* ui_services_note.md

Those files remain for reference only.
