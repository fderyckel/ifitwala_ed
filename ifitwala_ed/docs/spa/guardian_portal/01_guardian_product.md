# Guardian Portal — Product Contract (v0.1)

**Ifitwala_Ed — Authoritative**
Status: Draft (Phase-0)
Audience: Humans, coding agents
Scope: Guardian / Parent Portal only
Last updated: 2026-02-02

---

## 1. Purpose

The Guardian Portal exists to support **busy parents** by giving them a **clear, calm, and reliable understanding of what is happening with their family at school**, and what—if anything—requires their attention.

It is designed to be:

* parent-centric (not child-centric by default)
* time-oriented (today → next school days)
* signal-first (no noise, no internal jargon)
* legally safe (GDPR, consent, auditability)

---

## 2. Primary User

**Guardian**

A Guardian is a legally linked adult responsible for one or more enrolled Students.
Guardians may have **multiple children**, possibly across **different schools**.

Assumptions:

* Guardians are not system experts
* Guardians do not understand internal academic structures
* Guardians value clarity, trust, and predictability over control

---

## 3. Core Problem the Portal Solves

When a Guardian opens the portal, they want to quickly answer:

1. **What is happening with my family at school?**
2. **What does the next week look like?**
3. **Is anything wrong or needs my attention?**
4. **How can I support my children?**

The portal must answer these questions in **under 30 seconds**, without requiring navigation or prior knowledge.

---

## 4. Design Principles (Non-Negotiable)

### 4.1 Parent-Centric First

* The default view is **family-level**, not child-level
* Guardians are not required to select a child on entry
* Child-specific detail is available **only when needed**

### 4.2 Plain Language Only

The portal must **never expose internal system concepts**, including but not limited to:

* rotation days
* block numbers
* internal module names
* gradebook mechanics
* reporting internals

All scheduling and academic information must be translated into **plain, human language**.

---

### 4.3 Time-Oriented, Not Module-Oriented

Information is organized by **time horizon**, not by system module.

Primary horizon:

* Today
* Next school days (default = next 7 school days)

Secondary horizon:

* Recent past (for continuity and trust)

---

### 4.4 Signal Over Noise

The portal must:

* surface only information that matters to Guardians
* suppress internal or low-signal data
* avoid duplication across sections

If a piece of data does not help a Guardian **understand, prepare, or act**, it does not belong on the home surface.

---

### 4.5 Healthy Engagement (Anti-Surveillance Principle)

The Guardian Portal is designed to **support healthy parent–child–school relationships**, not continuous surveillance.

The system must **avoid patterns that encourage compulsive monitoring**, including but not limited to:

* real-time grade streams
* rolling averages visible at all times
* automated “performance drop” alerts
* constant numeric comparison surfaces

**Invariant**

> The Guardian Portal provides **situational awareness**, not continuous performance tracking.

Guardians are informed:

* when something is published
* when something requires attention
* when context is needed

Not:

* every time internal data changes
* before academic truth is finalized

This principle applies across:

* UX defaults
* notification cadence
* summary design
* data aggregation

---

### 4.6 Weekly Summary (Concept — Locked, Execution Deferred)

The system supports the concept of a **Weekly Guardian Summary**.

**Intent**

* Provide a calm, periodic overview of the family’s school life
* Reduce daily checking pressure
* Reinforce trust and routine

**Characteristics (conceptual)**

* Aggregated at family level
* Covers:

  * upcoming week highlights
  * recently published results
  * notable events or communications
* Narrative-first, not alert-driven

**Important**

* Weekly Summary is **not real-time**
* It does **not replace** Guardian Home
* It is **additive**, not mandatory

> Execution details (delivery channel, cadence, formatting) are intentionally deferred.

---

### 4.7 Accessibility & Inclusion

The Guardian Portal must be accessible and inclusive by default.

Baseline requirements:

* WCAG **AA** compliance target
* Keyboard navigation support
* Screen-reader friendly semantics
* Clear contrast and typography

Multilingual support:

* UI strings must be translatable
* Content translation is policy-driven
* Language preference is Guardian-scoped

Accessibility is a **core requirement**, not a future enhancement.

---

### 4.8 Communication Channel Intent (High-Level)

The Guardian Portal defines **intent**, not channel mechanics.

Principles:

* Not all information deserves interruption
* Redundant notifications create fatigue and distrust

High-level intent:

* Urgent, time-sensitive information → push-capable channel
* Non-urgent information → in-portal + digest
* No automatic multi-channel blasting by default

Detailed channel rules are defined in a separate contract.

---

### 4.9 Optional Monitoring Mode (Opt-In)

The Guardian Portal supports an **optional Monitoring Mode**, enabled only by
explicit Guardian choice.

#### Default State (Locked)
- Monitoring Mode is **disabled by default**
- The portal operates in **Awareness Mode**
- No real-time performance alerts
- No threshold-based grade notifications

This default reflects the system’s commitment to healthy engagement and
non-surveillance relationships.

#### Monitoring Mode (Opt-In)

When explicitly enabled by a Guardian, the system may provide:

- Near-real-time visibility of newly published task results
- Automated notifications when published results fall below configured thresholds

Monitoring Mode:
- Applies **per Guardian**, not globally
- Applies **per Student**, not per family
- Does **not** override publication rules
- Does **not** expose draft or unpublished data

#### Invariants

Monitoring Mode must never:
- expose live gradebook or draft grading
- bypass `published_to_parents` gates
- compare siblings
- impose default thresholds
- be enabled implicitly by staff or system actions

Monitoring is a **guardian choice**, not a system assumption.

---

## 5. What the Guardian Portal Guarantees

The Guardian Portal guarantees that:

* Guardians see **only data they are authorized to see**
* All visible academic results are **explicitly published to parents**
* All visible behaviour or health notes are **explicitly marked as guardian-visible**
* All acknowledgements and consents are **explicit, contextual, and auditable**
* No data shown is provisional, speculative, or internal-only

---

## 6. What the Guardian Portal Is NOT

The Guardian Portal is **not**:

* a live gradebook
* a staff tool
* a configuration interface
* a child comparison dashboard
* a system of record editor

Guardians may **view**, **acknowledge**, and **communicate**, but they may not:

* modify academic records
* modify relationships
* infer unpublished results
* access staff-only notes or drafts

---

## 7. Academic Information Contract (High-Level)

* All academic work is modeled internally as **Tasks**
* Tasks may represent:

  * assessments
  * homework
  * classwork
* Guardians see:

  * what is due
  * when it is due
  * high-level status
  * results **only after publication**
* Task instructions and detailed evidence are **hidden by default**, available on demand

---

## 8. Behaviour, Health, and Wellbeing Information

* Student Logs are visible to Guardians **only if explicitly marked**
* No severity labels are imposed by the system
* The portal does not interpret behaviour for Guardians
* Guardians decide what is serious for their family

---

## 9. Communication Contract

* The portal exposes a **canonical Communication stream**
* Communications are event-based (not threaded by default)
* Guardians may:

  * read
  * acknowledge
  * later respond (Phase-2)
* Communication visibility is explicit and audience-scoped

---

## 10. Legal, Consent, and Acknowledgement

* All legal acknowledgements follow the locked **Policy → Version → Acknowledgement** model
* No implicit consent
* No retroactive consent
* No consent by proxy
* Acknowledgements are:

  * contextual
  * append-only
  * auditable

The Guardian Portal is a **primary surface** for legal acknowledgements.

---

## 11. Actions (Intent Only — Phase-Aware)

The Guardian Portal may expose the following actions over time:

* Acknowledge policies / forms
* Book meetings
* Message staff
* Upload documents
* Pay fees

Actions are:

* contextual
* non-destructive
* never record-mutating

Availability may vary by phase, but **intent is locked**.

---

## 12. Explicit Non-Goals (Locked)

The Guardian Portal will **never**:

* compare siblings academically
* expose live grade calculations
* allow Guardians to edit core records
* expose internal staff commentary
* expose unpublished reporting data

---

## 13. Phase-0 Lock Statement

> This document defines the **product truth** of the Guardian Portal.
>
> All UX, IA, backend permissions, and future features must conform to this contract.
>
> Any deviation requires an explicit revision of this document.

---













## Next logical steps to implement the Guardian Portal

UI wiring is **not** the next step yet. The next step is to turn the contracts + IA into an **implementation spec** that Codex agents can execute without improvising (and without drifting).

### Step 1 — Write the “Guardian Portal Implementation Plan” (agent-ready)

Deliverable: one markdown spec that is explicit about **scope, phase, and acceptance checks**.

**File to create (repo):**

* `docs/portal/guardian/implementation_plan_phase1.md`

**Contents (must be explicit):**

* Phase-1 features (what ships)
* Non-goals (what is stubbed)
* Data surfaces for Guardian Home (4 zones)
* Required API endpoints (read-only first)
* Performance targets (no chatty APIs; aggregation server-side)
* Security/visibility gates (server-side)
* A+ ownership rules (who refetches, who signals, who toasts)

**Phase-1 recommended scope (minimal but real):**

* Guardian Home: Zones 1–4 working (read-only)
* “Attention Needed” includes:

  * unread Communications
  * guardian-visible Student Logs
  * pending Policies/Acknowledgements (if already in place)
* Task list: only “signal” tasks (due soon + published results recently)
* Monitoring Mode setting: **stub only** (no alerts yet), or exclude Phase-1 if not ready

### Step 2 — Produce the “Guardian Home Data Contract” (per zone)

Deliverable: a concrete mapping from IA → server responses.

**File to create:**

* `docs/portal/guardian/guardian_home_data_contract.md`

For each zone define:

* Input filters (guardian_id implicit, student list derived)
* Output shape (TS interface name, fields, types)
* Sorting rules
* Pagination rules (if any)
* Caching rules (Redis where stable)
* “Plain-language schedule” rules (no rotation/block leakage)

This is what prevents UI and agents from inventing shapes.

### Step 3 — Lock TypeScript contracts + service boundary (A+ compliant)

Deliverable: TS request/response contracts + service functions (no UI side effects).

**Files to create/update (likely):**

* `ui-spa/src/contracts/guardian/*.ts` (or your existing contracts folder structure)
* `ui-spa/src/services/guardian/guardianHomeService.ts`
* `ui-spa/src/lib/uiSignals.ts` (if new invalidation needed)
* Ensure transport boundary remains only in `ui-spa/src/resources/frappe.ts`

**A+ rules to enforce:**

* Services return domain payloads only
* Services may emit signals after mutation success (Phase-1 has almost no mutations)
* Pages/shell own refetch + toasts (Guardian shell likely owns “Saved/Acknowledged” later)

### Step 4 — Implement backend aggregation endpoints (read-only first)

UI wiring depends on this.

Deliverable: 1–2 server endpoints that return **all Guardian Home data in one response** (or one per zone at most). Avoid chatty calls.

**Implementation stance:**

* One “guardian_home_bundle” endpoint is best for performance and UX stability.
* It should return 4 arrays (timeline, attention, prep, recent) already visibility-filtered.

**Where (example):**

* `ifitwala_ed/portal/api/guardian_home.py` (or your canonical API location)

### Step 5 — Implement Guardian Home page as a Refresh Owner (UI wiring)

Only after steps 1–4 are locked.

Deliverable: GuardianHome.vue uses the service and renders zones with progressive disclosure.

**A+ compliance:**

* Page owns loading + error states
* Inline expand is UI-only state
* No toasts inside components; shell decides later
* No hardcoded `/portal` paths inside SPA (use named routes / base-less paths)

### Step 6 — Codex agent task slicing (execution plan)

Turn steps 2–5 into **small PR-sized tasks** (one file/concern per task).

Example slices:

1. Add TS contracts for GuardianHome bundle
2. Add backend endpoint returning stubbed bundle
3. Connect GuardianHome.vue to display skeleton + empty states
4. Implement Communications part end-to-end
5. Implement Tasks part end-to-end
6. Implement Student Logs part end-to-end
7. Implement Policies/Acknowledgements part end-to-end

Each slice has:

* exact files touched
* acceptance checks
* no schema invention allowed

---

## Files I need from you before I can write the agent-ready implementation plan

Per your governance rules: I will not invent doctypes/fields/endpoints. Please share the **authoritative sources** below (paste or upload). I’m listing only what’s necessary for Phase-1 Guardian Home.

### A) SPA structure

1. `ui-spa/src/resources/frappe.ts`
2. Router file(s) that define guardian routes (e.g. `ui-spa/src/router/...`)
3. `ui-spa/src/lib/uiSignals.ts`
4. Any existing `services/` folder structure and naming conventions (one example service file)

### B) Current Guardian Portal pages/components

You already uploaded:

* `GuardianHome.vue`
* `GuardianStudentShell.vue`
  Also share:

5. Guardian layout/shell used by portal (if different)
6. Any existing “cards” or timeline components you want reused

### C) Doctype + API truth (must-have)

7. **Communication** DocType JSON + server code that determines audience scoping
8. **Student Log** DocType JSON + fields controlling guardian visibility (`visible_to_guardians` etc.)
9. **Task / Task Outcome** doctypes (or your current equivalents) including `published_to_parents` mechanism
10. **School Calendar** doctype (holidays/weekends/events)
11. The doctype(s) for Guardian↔Student relationship (how we derive “my children”)

### D) Policy/Acknowledgement system (only if included Phase-1)

12. Policy + Policy Version + Policy Acknowledgement doctypes (or whatever you have)

---

## What I will do immediately after you share those files

1. Produce `implementation_plan_phase1.md` (agent-ready, no drift)
2. Produce `guardian_home_data_contract.md` with explicit TS types
3. Define backend endpoint signatures and query strategy (low DB round-trips, Redis for stable lookups)
4. Break it into Codex tasks with “done” checks

Send the files in any order. If you want the fastest path: start with **Task/Outcome**, **Student Log**, **Communication**, and the **Guardian↔Student link doctype**.
