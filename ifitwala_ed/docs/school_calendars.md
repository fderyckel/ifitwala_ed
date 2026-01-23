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
Here’s the correct distinction.

### ❌ What a parent-level calendar must **NOT** be

* Not the “real” instructional calendar for leaf schools
* Not something students or teachers operate against
* Not a place where term logic is inferred downward
* Not a source of automatic term instantiation

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
  * **must not auto-resolve instructional terms**
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

### **Answer: YES — but strictly as templates (Option B)**

Global terms are dangerous *unless their role is explicit*.
This is where **Option B** is now locked.

### ❌ What global terms must NOT be

* Active instructional terms
* Automatically instantiated into schools
* Generators of School Events
* Counted in analytics without explicit resolution

### ✅ What global terms ARE (Option B)

> **Reusable, non-operational term templates scoped to an Academic Year**

Examples:

* “Semester 1 / Semester 2”
* “Trimester A / B / C”
* “Quarter 1–4”
* “IB Term Structure”

### 🔐 Rule (Option B — Canonical)

> A Term with `school = null` is a **template only**.
> It **never becomes active** unless resolved by a School Calendar.

### Activation semantics

Global terms may be:

* **resolved at runtime** (calendar, enrollment, analytics)
* **instantiated explicitly** (copy/create) with user confirmation

They must **never**:

* create School Events
* appear in instructional analytics
* silently populate child schools

✔ Global terms are allowed
❌ Global terms are never operational by default

---

## 3️⃣ Should School Calendars auto-populate terms?

### **Answer: YES — but only via explicit Option B resolution**

Auto-population is correct **only if deterministic, visible, and reversible**.

### Safe auto-population hierarchy (LOCKED)

When creating or validating a School Calendar:

1. **School-specific terms exist**
   → Auto-populate **those only**
2. **No school terms, but global templates exist**
   → Resolve via **Option B** (no mutation)
3. **Nothing exists**
   → Empty calendar + explicit warning

### 🔐 Hard rules

* Auto-population must:

  * be reviewable
  * be reversible
  * never create terms silently
* Resolution must:

  * record source (`school | template`)
  * never guess inheritance
* Only **school-scoped terms** may:

  * generate School Events
  * drive instructional counts

✔ Auto-population is correct
❌ Blind inheritance is forbidden

---

## 🧠 Final Unified Mental Model (Option B Explicit)

```
Academic Year (IIS)
│  └─ Hard temporal container
│
├── Global Term Templates (school = null)
│   └─ Non-operational, no events, no analytics
│
├── Parent School Calendar (IIS)
│   └─ Non-instructional baseline (holidays only)
│
├── School (ISS)
│   ├── Terms (ISS-specific)
│   └── School Calendar (ISS)
│       ├── Academic Year = IIS
│       ├── Terms = resolved via Option B
│       └── Overlays parent calendar
│
└── School (IPS)
    ├── Terms (IPS-specific)
    └── School Calendar (IPS)
```

---

## 🔒 Governance Rules (Updated)

1. Academic Year is the sole outer temporal boundary.
2. Terms are pedagogical and school-scoped **or templates**.
3. Global terms are templates, never active by default.
4. School Calendars resolve terms explicitly (Option B).
5. Parent calendars are allowed but non-instructional.
6. Auto-population is allowed; silent inheritance is forbidden.
7. Only school-scoped terms may generate School Events.

---

---

# 📘 `academic_time_governance.md`

> **Status:** LOCKED (v1.1 — Option B)
> **Scope:** Academic Year, Term, School Calendar
> **Authority:** This document governs all academic-time behavior in Ifitwala_Ed.
> Any implementation (Desk, SPA, API, reports, analytics) **must conform**.

---

## 1. Core Intent

Ifitwala_Ed models academic time using **explicit resolution**, not inheritance.

**Option B is canonical**:

> Terms are resolved by context, never auto-instantiated.

The system must support:

* multi-campus institutions
* divergent term structures
* shared closures and constraints
* deterministic analytics
* safe future extensions (accreditation, cross-school reporting)

---

## 2. Canonical Objects and Roles

### 2.1 Academic Year (AY)

*(unchanged, reaffirmed)*

* Hard temporal container
* Outer boundary
* No downward inference

---

### 2.2 Term

**Rules (clarified)**

* Every Term belongs to:

  * exactly one Academic Year
  * either:

    * one School (active term)
    * no school (template)

#### Global Terms (Option B)

* `school = null`
* Templates only
* Never:

  * create events
  * appear in analytics
  * auto-populate schools
* Only resolved via School Calendar

---

### 2.3 School Calendar (Canonical, Option B)

> A School Calendar represents the **resolved operational calendar**
> for one school in one academic year.

**Rules**

* Always school-scoped
* Always AY-scoped
* Resolves terms via:

  * school terms first
  * global templates second
* Never mutates term data implicitly

---

### 2.4 Parent-Level School Calendars

*(clarified)*

* Allowed
* Non-instructional
* Holiday-only
* Never resolve instructional terms

---

## 3. Term Resolution Rules (Option B)

Resolution is **read-only** and **deterministic**.

1. School-specific terms
2. Global templates
3. Nothing → empty calendar

**Silent inheritance is forbidden.**

---

## 4. Analytics & Reporting (Option B Safe)

* Analytics operate only on:

  * resolved school terms
* Templates excluded unless resolved
* Parent calendars affect:

  * blackout windows
  * holiday overlays only

---

## 5. Invariants (Expanded)

1. Academic Year is the sole outer boundary
2. Templates are never operational
3. Calendars resolve, not inherit
4. Events come only from school terms
5. Automation must be explicit and reversible

---

## 🧰 Helper (Canonical)

### `resolve_terms_for_school_calendar(school, academic_year)`

**Status:** Canonical (Option B)

* Read-only
* Deterministic
* No mutation
* Used by:

  * School Calendar
  * Enrollment
  * Attendance
  * Analytics

---

## 🔚 Final Position (Locked)

You now have:

* Explicit Option B semantics
* Clean separation of template vs operational data
* Zero inheritance magic
* Analytics-safe resolution
* A framework that scales across jurisdictions and pedagogy

---










# 🔐 Invariant → Enforcement Map (Ifitwala_Ed)

---

## **Invariant 1**

### **Academic Year is the sole outer temporal boundary**

> Nothing (Term, Calendar, Holiday, Attendance, Enrollment) may escape AY dates.

### Enforced in

#### ✅ `Term`

**File**

```
ifitwala_ed/school_settings/doctype/term/term.py
```

**Controller**

```python
Term.validate()
```

**Rules enforced**

* `term_start_date >= ay.year_start_date`
* `term_end_date <= ay.year_end_date`

**Status**
✅ Enforced
🔒 Canonical

---

#### ⚠️ `School Calendar Holidays`

**File**

```
ifitwala_ed/school_settings/doctype/school_calendar/school_calendar.py
```

**Controller**

```python
SchoolCalendar.validate_dates()
```

**Rules enforced**

* Holiday dates ∈ AY range

**Status**
✅ Enforced
🔒 Canonical

---

#### ⚠️ Enrollment / Attendance

**Files**

```
Program Enrollment
Student Attendance
```

**Status**
🟡 **Implicit today** (derived via Term / Calendar)
🔜 **Expected to be enforced via resolved term window**, not AY directly

**Why**
Correct by design — enforcement belongs to **resolved operational window**, not raw AY.

---

## **Invariant 2**

### **Terms never cross schools implicitly**

> No sibling or parent/child leakage.

### Enforced in

#### ✅ `Term`

**File**

```
ifitwala_ed/school_settings/doctype/term/term.py
```

**Controller**

```python
Term._sync_school_with_ay()
Term.validate_duplicate()
```

**Rules enforced**

* `Term.school` must be:

  * AY.school **or**
  * descendant of AY.school
* `(academic_year, term_name, school)` uniqueness

**Status**
✅ Enforced
🔒 Canonical

---

#### 🚫 Explicitly forbidden elsewhere

* No controller auto-copies terms
* No calendar pulls sibling terms
* No inheritance in queries

**Status**
✅ Safe by absence (correct)

---

## **Invariant 3**

### **Global terms are templates, never operational**

> `school = null` ≠ active term

### Enforced in

#### ✅ `Term → School Event creation`

**File**

```
ifitwala_ed/school_settings/doctype/term/term.py
```

**Controller**

```python
Term.on_update()
Term.create_calendar_events()
```

**Rule**

```text
Only school-scoped terms may create School Events
```

**Implementation**
You explicitly refactored:

* Global terms → **no events**
* School terms → events allowed

**Status**
✅ Enforced
🔒 Canonical

---

#### ✅ `resolve_terms_for_school_calendar`

**File**

```
ifitwala_ed/school_settings/school_settings_utils.py
```

**Helper**

```python
resolve_terms_for_school_calendar()
```

**Rule**

* Global terms returned **only if no school terms**
* No mutation
* No activation

**Status**
✅ Enforced by design
🔒 Canonical Option B

---

## **Invariant 4**

### **School Calendars are explicit, not inferred**

> Calendars resolve terms; they never guess.

### Enforced in

#### ✅ `School Calendar`

**File**

```
ifitwala_ed/school_settings/doctype/school_calendar/school_calendar.py
```

**Controllers**

```python
SchoolCalendar._sync_school_with_ay()
SchoolCalendar._validate_uniqueness()
```

**Rules enforced**

* One calendar per `(school, academic_year)`
* School ∈ AY hierarchy
* No auto-creation from AY alone

**Status**
✅ Enforced
🔒 Canonical

---

#### 🟡 `_populate_term_table`

**File**

```
school_calendar.py
```

**Current behavior**

* Pulls **school-scoped terms only**

**Gap (intentional, next step)**

* Must switch to:

```python
resolve_terms_for_school_calendar()
```

**Status**
🟡 Partial
🔜 Next refactor target (known and isolated)

---

## **Invariant 5**

### **Parent calendars are non-instructional**

> Parent ≠ pedagogical authority

### Enforced in

#### 🟡 `School Calendar.validate()`

**File**

```
school_calendar.py
```

**Current state**

* Parent calendars allowed
* No instructional enforcement yet

**Missing enforcement**

* Block instructional term resolution when:

```text
School.is_group == 1
```

**Status**
🟡 **Governance locked**
🔜 **Validation stub pending (already specified)**

**Correct place to enforce**

```python
SchoolCalendar.validate()
```

---

## **Invariant 6**

### **Automation must be visible and reversible**

> No silent inheritance. Ever.

### Enforced in

#### ✅ Absence of mutation

**Files**

```
term.py
school_calendar.py
school_settings_utils.py
```

**Facts**

* No auto-instantiation of terms
* No background creation
* All actions are:

  * explicit
  * user-triggered
  * reversible

**Status**
✅ Enforced by architecture
🔒 Canonical

---

## **Invariant 7**

### **Only school-scoped terms may generate events**

> Templates never create operational artifacts.

### Enforced in

#### ✅ `Term.create_calendar_events()`

**File**

```
term.py
```

**Rule**

```text
if not self.school → no School Event
```

**Status**
✅ Enforced
🔒 Canonical

---

# 📌 Summary Table (Quick Scan)

| Invariant                | File                       | Controller / Helper                   | Status     |
| ------------------------ | -------------------------- | ------------------------------------- | ---------- |
| AY ⊂ All                 | `term.py`                  | `Term.validate()`                     | ✅          |
| AY ⊂ Holidays            | `school_calendar.py`       | `validate_dates()`                    | ✅          |
| No term inheritance      | `term.py`                  | `_sync_school_with_ay()`              | ✅          |
| Global terms = templates | `school_settings_utils.py` | `resolve_terms_for_school_calendar()` | ✅          |
| No global events         | `term.py`                  | `create_calendar_events()`            | ✅          |
| Calendar explicitness    | `school_calendar.py`       | `_validate_uniqueness()`              | ✅          |
| Parent non-instructional | `school_calendar.py`       | `validate()`                          | 🟡 pending |
| Automation visibility    | architecture               | no mutation                           | ✅          |

---

