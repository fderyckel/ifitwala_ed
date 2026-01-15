# UI Services + Overlay Lifecycle Contract (SPA)
**Status:** Proposed (lock once implemented)
**Audience:** Humans + coding agents
**Applies to:** `ui-spa/src/*` (Vue SPA), especially overlays and workflow actions
**Motivation:** End recurring “toast unavailable” + “overlay doesn’t close” failures caused by provider timing, Teleport boundaries, and stacked overlays.

---

## 1) Problem we are solving (blunt)
We have recurring UI failures that look “silent”:
- Success toast sometimes logs **toast unavailable** or fails to render.
- After submit, an overlay sometimes **does not close**, even though the workflow completed.
- These failures are expensive to debug because they’re **timing / lifecycle** issues (Teleport + stacked overlays + app boot).

Ifitwala_ed will become a cloud platform with many workflows and long-lived sessions. These issues will scale badly:
- more workflows = more places to break
- more overlays = more lifecycle edge cases
- longer sessions = more “state drift” bugs

**We need a platform-level contract.**

---

## 2) Design principles (non-negotiable)
### P1 — Leaf components must not assume providers exist
Overlays and workflow components must never depend on:
- `toast` provider being present
- a parent remembering to flip `open=false`
- route state being stable

They must call stable, app-owned APIs.

### P2 — Single choke points (boring + observable)
- One ToastHost mounted once.
- One OverlayHost controlling stack state.
- Leaf components request actions; hosts execute actions.

### P3 — Names must avoid collisions with Frappe/Frappe-UI
Avoid names like:
- `get_context`, `getContext`, `context`, `resource`, etc. in our platform layer.
Use explicit names:
- `resolve_focus_payload`, `fetch_focus_payload`
- `uiNotify`, `overlayRequestClose`
- `focusPayload`, `overlayEntry`, `uiBus`

---

## 3) UX Contract (what users can rely on)
### U1 — After a successful “submit action”
- A success notification is shown (or queued if UI isn’t ready).
- The current overlay closes **deterministically**.
- The parent list (Focus / etc.) refreshes via a stable event.

### U2 — On error
- The overlay stays open.
- The user sees a clear error notification.
- The user can retry safely (idempotency supported server-side).

### U3 — No duplicate spam
- UI notifications can dedupe using a `dedupeKey` (typically `client_request_id`).

---

## 4) Architecture fit (overall SPA)
This is part of the **UI platform layer**:
- **Domain layer:** Focus workflows, Student Log workflows, etc.
- **UI platform layer (this note):** Notifications + overlay lifecycle + global UI event bus
- **UI shell:** Layouts + router + mount points

**Domain components call platform APIs.**
They do not talk to providers directly.

---

## 5) Implementation plan (specific)

### 5.1 Create a minimal app-owned UI event bus
**Goal:** cross-tree signaling that survives Teleport and overlay stacking.

**Create**
- `ui-spa/src/ui/ui_bus.ts`

**Exports**
- `uiBus.on(eventName, handler)`
- `uiBus.emit(eventName, payload)`
- `uiBus.off(eventName, handler)` (if using mitt)

**Event names (string constants)**
- `UI_NOTIFY` (notifications)
- `FOCUS_REFRESH` (already exists conceptually; standardize naming)
- (Optional later) `UI_ERROR_REPORT`, `RESOURCE_INVALIDATE:*`

**Naming rule**
- Use `IF_` prefix to avoid collisions, e.g. `IF_UI_NOTIFY`.

---

### 5.2 Create a Notification Service (do not call it “toast”)
**Goal:** leaf components call one stable API: `uiNotify.*()`

**Create**
- `ui-spa/src/ui/ui_notify.ts`

**API**
- `uiNotify.success({ title, text?, dedupeKey?, durationMs? })`
- `uiNotify.error({ title, text?, dedupeKey?, durationMs? })`
- `uiNotify.info(...)`

**Under the hood**
- emits `IF_UI_NOTIFY` on `uiBus`

**Rules**
- No component outside `src/ui/*` may import `toast` from `frappe-ui`.
- Components must call `uiNotify`.

---

### 5.3 Create a single ToastHost mounted once (top of SPA)
**Goal:** one place in the app is responsible for rendering notifications.

**Create**
- `ui-spa/src/components/ui/ToastHost.vue`

**Behavior**
- Subscribes to `IF_UI_NOTIFY`
- Renders notifications:
  - Option A: delegates to `frappe-ui` `toast()` if available
  - Option B: renders our own toast UI (future)
- Implements:
  - dedupe by `dedupeKey`
  - optional queue until “ready” (if needed)
  - safe fallback if frappe-ui toast is not available

**Mount location**
- In the SPA root shell component that is always present:
  - likely `App.vue` or a root layout like `StaffLayout.vue`
- Must be mounted **above** OverlayHost and router views.

**Do not name it**
- `ToastProvider`, `ToastContext`, `get_context`, etc.

---

### 5.4 Overlay Lifecycle Contract (deterministic close)
**Goal:** overlays close reliably in stacked overlay environments.

#### Contract
1. Overlays are opened via `useOverlayStack`.
2. Overlays close via `useOverlayStack` (not by hoping a parent handles `emit('close')`).

#### Requirements
- Every overlay entry has an `id` (already true).
- Every overlay component receives `overlayId` as a prop (passed by OverlayHost).

**OverlayHost changes**
- When rendering a component, pass:
  - `:overlay-id="entry.id"`
- Standardize emits:
  - `@request-close="requestClose(entry.id)"` (optional)
  - but ideally overlay calls stack close directly

**Overlay stack API changes**
- `requestClose(id)` => sets `entry.open=false` (starts leave transition)
- `finalizeClose(id)` => removes entry after `after-leave`
- `closeTop()` convenience
- `close(id)` convenience (calls requestClose)

**Leaf overlay behavior**
- On success:
  1) `uiNotify.success(...)`
  2) dispatch domain refresh event (e.g. `IF_FOCUS_REFRESH`)
  3) close itself via overlay stack (`close(overlayId)`)

**Do not rely on**
- emitting `close` and hoping the parent flips `open`
- direct `Dialog @close` behavior to do all lifecycle cleanup

---

## 6) Refactor plan (what to change in existing code)

### 6.1 Replace direct `toast(...)` usage
Search and refactor:
- `import { toast } from 'frappe-ui'`  ❌
Replace with:
- `import { uiNotify } from '@/ui/ui_notify'` ✅

Then replace calls:
- `toast({ title, text, icon })`
with:
- `uiNotify.success({ title, text, dedupeKey })`
- `uiNotify.error({ title, text })`

**Files likely impacted**
- `ui-spa/src/components/student/StudentLogCreateOverlay.vue`
- `ui-spa/src/components/student/StudentLogFollowUpOverlay.vue`
- `ui-spa/src/components/focus/StudentLogFollowUpAction.vue`
- `ui-spa/src/components/focus/FocusRouterOverlay.vue`
- any other overlays / workflow components

---

### 6.2 Standardize overlay closing (stop “silent close”)
We will implement a single success pattern:

**Success pattern**
- `await apiCall()`
- `uiNotify.success(...)`
- `emit('done')` (domain refresh intent) OR `uiBus.emit(IF_FOCUS_REFRESH)`
- `overlay.close(overlayId)` OR `emit('close')` ONLY if parent is guaranteed to close via overlay stack

**Rule**
If the overlay is hosted by OverlayHost stack:
- it must close via stack API.

**Files**
- `OverlayHost.vue` (pass overlayId)
- `useOverlayStack.ts` (ensure close methods exist)
- each overlay component (call close API)

---

### 6.3 Standardize domain refresh event naming
We already have `ifitwala:focus:refresh`.
We will:
- rename constant to `IF_FOCUS_REFRESH` (string stays stable if you want)
- centralize constants in one place:
  - `ui-spa/src/ui/events.ts`

Overlays should not invent new event strings inline.

---

## 7) What to pay attention to (failure modes)

### 7.1 Provider timing + Teleport
- A component inside Teleport may render outside the provider tree.
- That is why we do not depend on provider injection for notifications.

### 7.2 Overlay stacking + inert layers
- Only the top overlay is interactive.
- A close request must target the correct overlay id.
- Always pass `overlayId` explicitly.

### 7.3 HeadlessUI close callback
- HeadlessUI `@close` is not a guarantee of teardown.
- It can be blocked by parent state not changing.
- Our contract: **OverlayHost controls the stack and teardown.**

### 7.4 Idempotency and double clicks
- Client creates `client_request_id`.
- Server already supports idempotency for follow-up submit/review.
- UI should also dedupe toasts using `dedupeKey=client_request_id`.

### 7.5 Naming collisions
Avoid in our platform layer:
- `context`, `get_context`, `getContext`
- `resource` (frappe-ui uses this concept heavily)
Use:
- `payload`, `resolve`, `fetch`, `uiBus`, `uiNotify`, `overlayEntry`

---

## 8) Pros / Cons (critical analysis)

### Pros
- **Deterministic UX:** success always closes overlay + shows message.
- **Less debugging:** one place to inspect notification behavior.
- **Future-proof:** can replace frappe-ui toast implementation later with no domain refactors.
- **Cloud-friendly:** long sessions + many workflows stay stable; dedupe reduces spam.

### Cons / Added complexity
- Adds a small platform layer (bus + host + notify API).
- Requires discipline and refactor pass.
- Slight “indirection” cost for devs (but saves time overall).

### Why this is worth it for Ifitwala_ed SaaS
As workflows grow, random UI lifecycle failures become the #1 trust killer.
A stable UI contract is a SaaS advantage:
- fewer “it didn’t work” support tickets
- more predictable behavior across updates
- easier onboarding for new contributors/agents

---

## 9) Definition of Done (DoD)
1. `ToastHost` is mounted once in SPA root.
2. All overlays/workflows use `uiNotify` (no direct frappe-ui toast imports outside `src/ui/*`).
3. OverlayHost passes `overlayId`; overlays close via overlay stack API.
4. Focus workflow:
   - submit follow-up => toast shows + overlay closes + focus list refreshes
   - review outcome => toast shows + overlay closes + focus list refreshes
5. No console warning: “toast unavailable”.
6. Add a short section in `AGENTS.md` referencing these hard rules.

---

## 10) Immediate next actions (for coding agent)
1. Create:
   - `ui-spa/src/ui/ui_bus.ts`
   - `ui-spa/src/ui/events.ts`
   - `ui-spa/src/ui/ui_notify.ts`
   - `ui-spa/src/components/ui/ToastHost.vue`
2. Mount `<ToastHost />` in SPA root shell component.
3. Update `OverlayHost.vue` to pass `overlayId`.
4. Ensure `useOverlayStack.ts` exposes `close(id)` / `requestClose(id)` properly.
5. Refactor existing overlays/workflows to:
   - use `uiNotify`
   - close via overlay stack contract
   - use centralized event constants

---
