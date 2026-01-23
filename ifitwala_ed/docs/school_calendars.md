# 🔒 Canonical Proposal — Academic Time Architecture (Ifitwala_Ed)

## 0. Non-negotiable temporal invariant (lock this first)

**Academic Year (AY)**

* Default duration: **exactly one full academic cycle**
  → e.g. **01 Sep → 31 Aug**
* AY is a **hard outer boundary**
* **Nothing escapes it**:

  * Terms ⊂ AY
  * Breaks ⊂ AY
  * Calendars ⊂ AY
  * Attendance ⊂ AY
  * Enrollment ⊂ AY

This is *not just convention* — it enables:

* deterministic analytics
* clean rollover
* predictable archival
* accreditation alignment

You already model this correctly.

---

## 1️⃣ Should a School Calendar exist at a parent level (IIS)?

### **Answer: YES — but with a constrained semantic role**

This is where most systems get this wrong.
Here’s the correct distinction:

### ❌ What a parent-level calendar must **NOT** be

* Not the “real” instructional calendar for leaf schools
* Not something students or teachers operate against
* Not a place where term logic is inferred downward

### ✅ What a parent-level calendar **IS**

A **baseline operational calendar** for:

* shared holidays
* statutory closures
* non-instructional institutional events
* region-wide constraints

Think:

* National holidays
* Ministry closures
* Accreditation blackout dates
* Org-wide PD days

### 🔐 Rule

> A **parent-school calendar is allowed**, but it is **non-instructional by default**.

### Concrete implications

* Parent calendar:

  * has **Academic Year**
  * has **holidays / breaks**
  * **may or may not** have terms
* Leaf calendars:

  * are **instructional**
  * may **overlay** parent calendar dates
  * never inherit terms implicitly

### Why this is future-proof

* Works for:

  * multi-country orgs
  * IB vs local programs
  * partial campus closures
* Avoids forcing leaf schools into identical pedagogical structures

✔ Your instinct (“I am thinking yes”) is correct
✳ But only if we **downgrade its authority**

---

## 2️⃣ Allow “global terms” (school = null)?

### **Answer: YES — but strictly as templates**

Global terms are dangerous *unless their role is explicit*.

### ❌ What global terms must NOT be

* Active instructional terms
* Automatically used by calendars
* Counted in analytics without resolution

### ✅ What global terms ARE

> **Reusable term templates scoped to an Academic Year**

Examples:

* “Semester 1 / Semester 2”
* “Trimester A / B / C”
* “Quarter 1–4”
* “IB Term Structure”

### 🔐 Rule

> A Term with `school = null` is a **template**, not an active term.

### Activation rule

A term becomes **active** only when:

* It is explicitly linked to a **School Calendar**
* AND resolved to a **school context**

This can be done by:

* copying
* instantiating
* or linking with explicit confirmation

### Why this matters

* Lets you ship:

  * default structures
  * curriculum-driven term patterns
* Without polluting operational data
* Without breaking per-school analytics

✔ Keep global terms
❌ Never treat them as operational by default

---

## 3️⃣ Should School Calendars auto-populate terms?

### **Answer: YES — but never silently**

Auto-populate is good **only if the rule is deterministic and visible**.

### Safe auto-population hierarchy

When creating a School Calendar (SC):

1. **Exact school terms exist**
   → Auto-populate those
2. **No school terms, but global terms exist**
   → Offer to instantiate global terms for that school
3. **Nothing exists**
   → Empty calendar, explicit warning

### 🔐 Hard rule

> Auto-population must be **reviewable and reversible**

Meaning:

* Populate on `after_insert`
* Mark rows as:

  * `source = school | global`
* Allow “Clear & Rebuild Terms” safely

### Why this is future-proof

* Fast setup for common cases
* Zero magic
* No silent coupling
* Allows migrations and refactors later

✔ Auto-populate is correct
❌ Blind inheritance is not

---

## 🧠 Final Unified Mental Model

```
Academic Year (IIS)
│  └─ Hard temporal container
│
├── Global Term Templates (school = null)
│
├── Parent School Calendar (IIS)
│   └─ Non-instructional baseline
│
├── School (ISS)
│   ├── Terms (ISS-specific)
│   └── School Calendar (ISS)
│       ├── Academic Year = IIS
│       ├── Terms = ISS only
│       └── Overlays parent calendar
│
└── School (IPS)
    ├── Terms (IPS-specific)
    └── School Calendar (IPS)
```

---

## 🔒 Governance Rules (ready to document)

You can literally paste this into a governance doc:

1. Academic Year is the sole outer temporal boundary.
2. Terms are pedagogical and school-scoped (or templates).
3. School Calendar is always school-scoped and explicit.
4. Parent calendars are allowed but non-instructional.
5. Global terms are templates, never active by default.
6. Auto-population is allowed, silent inheritance is forbidden.

---













# 📘 `academic_time_governance.md`

> **Status:** LOCKED (v1)
> **Scope:** Academic Year, Term, School Calendar
> **Authority:** This document governs all academic-time behavior in Ifitwala_Ed.
> Any implementation (Desk, SPA, API, reports, analytics) **must conform**.

---

## 1. Core Intent

Ifitwala_Ed models academic time using **explicit, layered containers**, not inheritance.

The system must support:

* multi-campus institutions
* divergent term structures
* shared closures and constraints
* deterministic analytics
* safe future extensions (accreditation, cross-school reporting)

---

## 2. Canonical Objects and Roles

### 2.1 Academic Year (AY)

**Definition**
A **hard temporal container** defining one full academic cycle.

**Rules**

* Default duration: **01 September → 31 August**
* AY is the **outermost boundary**
* Nothing may exist outside its date range:

  * Terms
  * Breaks
  * Calendars
  * Instructional days
* AY may be:

  * **Global** (parent school)
  * **School-scoped** (exceptional cases)

**AY never infers structure downward.**

---

### 2.2 Term

**Definition**
A **pedagogical segmentation** of an Academic Year.

**Rules**

* Every Term belongs to:

  * exactly one **Academic Year**
  * either:

    * one **School** (active term), or
    * **no school** (template term)
* Term dates must be fully contained within the AY.

#### Global Terms (`school = null`)

* Are **templates**, not operational objects
* May represent:

  * Semester / Trimester / Quarter patterns
* Never active by default
* Must be explicitly instantiated or resolved to a school

---

### 2.3 School Calendar

**Definition (Canonical)**

> A **School Calendar represents the operational calendar for one school in one academic year, using that school’s own terms.**

**Rules**

* A School Calendar:

  * is always scoped to **exactly one School**
  * references **exactly one Academic Year**
  * uses **only terms belonging to that school**
* A School Calendar **never infers terms from Academic Year**

---

### 2.4 Parent-Level School Calendars

Parent schools (e.g. IIS) **may have calendars**, but with constrained semantics.

**Parent Calendar Role**

* Non-instructional baseline
* Defines:

  * national holidays
  * statutory closures
  * organization-wide events
* May be overlaid by child schools

**Prohibition**

* Parent calendars must not:

  * define instructional terms for children
  * silently propagate structure

---

## 3. Term Resolution Rules

When a School Calendar is created:

1. If school-specific terms exist → use them
2. Else if global term templates exist → offer instantiation
3. Else → calendar remains empty with warning

**Silent inheritance is forbidden.**

---

## 4. Analytics & Reporting Implications

* Instructional analytics always operate on:

  * `(school, academic_year, resolved_terms)`
* Global terms are excluded unless instantiated
* Parent calendars affect:

  * holiday counts
  * blackout windows
  * compliance views

---

## 5. Invariants (Non-Negotiable)

1. Academic Year is the sole outer boundary
2. Terms never cross schools implicitly
3. Calendars are explicit, not inferred
4. Templates are not operational
5. Automation must be visible and reversible

---

# ✅ Validations (3)

These are **server-side**, enforced via **Document controllers** (`validate` / `before_save`).

---

## Validation 1 — Term ⊂ Academic Year

**Where:** `Term.validate()`

**Rule**

* `term_start_date >= academic_year.year_start_date`
* `term_end_date <= academic_year.year_end_date`

**Failure**

```
Term dates must be fully contained within the Academic Year.
```

**Why**

* Prevents analytical corruption
* Guarantees deterministic rollups

---

## Validation 2 — School Calendar Term Ownership

**Where:** `School Calendar.validate()`

For each row in `School Calendar Term`:

**Rules**

* `term.academic_year == school_calendar.academic_year`
* `term.school == school_calendar.school`

**Explicitly forbid**

* linking global terms directly
* linking sibling-school terms

**Failure**

```
Only terms belonging to the selected school and academic year may be used in this calendar.
```

---

## Validation 3 — Parent Calendar Non-Instructional Guard

**Where:** `School Calendar.validate()`

If:

* `school.is_group == 1` (parent school)

Then:

* either:

  * no terms allowed **OR**
  * all terms must be marked `instructional = 0` (future-ready)

**Failure**

```
Parent school calendars cannot define instructional terms.
```

**Why**

* Preserves hierarchy semantics
* Avoids accidental propagation

---

# 🧰 Helper (1)

## `resolve_school_calendar_terms(school, academic_year)`

**Purpose**
Deterministic, explicit term resolution for calendar creation.

**Behavior**

1. Fetch school-specific terms for `(school, academic_year)`
2. If found → return them
3. Else fetch global term templates for `(academic_year)`
4. Return templates with `source = "template"`

**Never**

* creates data silently
* mutates terms
* guesses inheritance

**Used by**

* School Calendar `after_insert`
* Setup wizards
* Future CLI / migration tools

---

# 🔚 Final Position (Locked)

You now have:

* Explicit temporal semantics
* Controlled hierarchy behavior
* Safe automation
* Zero magic inheritance
* A framework that scales to:

  * multi-country orgs
  * accreditation regimes
  * divergent pedagogy

Next step, **only if you want**:

* map these rules to the exact files you shared
* write the validation stubs (no guessing)
* add the helper in `school_settings_utils.py`

Say **“Proceed to implementation mapping”** when ready.
