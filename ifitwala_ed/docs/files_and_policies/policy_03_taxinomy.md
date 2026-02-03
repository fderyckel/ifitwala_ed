# ✅ Policy Taxonomy — **LOCKED v1**

> This taxonomy defines **what kinds of policies exist** in the system.
> It does **not** define enforcement, workflows, or UI behavior.

Once locked, **no new category is added casually**.
If a policy doesn’t fit, it’s a *content problem*, not a schema problem.

---

## 1️⃣ Canonical Policy Categories (Authoritative)

### 1. **Safeguarding**

**Purpose:** Protect students and vulnerable persons.

**Typical content**

* Child Protection Policy
* Safeguarding & Reporting Obligations
* Staff Code of Professional Conduct (safeguarding-related)

**Applies to**

* Staff
* Students (acknowledgement)
* Contractors / Volunteers (future)

**Notes**

* High legal sensitivity
* Often mandatory, but *requirement is external*

---

### 2. **Privacy & Data Protection**

**Purpose:** Regulate data use, consent, and visibility.

**Typical content**

* Data Privacy Notice
* Media / Image Consent
* Data Retention Policy

**Applies to**

* Applicants
* Students
* Guardians
* Staff

**Notes**

* Versioning is critical
* Jurisdiction-sensitive but taxonomy-stable

---

### 3. **Admissions**

**Purpose:** Govern pre-student processes and expectations.

**Typical content**

* Admissions Terms & Conditions
* Medical Disclosure Statement
* Admissions Agreement

**Applies to**

* Applicants
* Guardians

**Notes**

* Lives fully in **Applicant stage**
* Never copied to Student implicitly

---

### 4. **Academic**

**Purpose:** Define learning, assessment, and integrity expectations.

**Typical content**

* Academic Integrity Policy
* Assessment & Grading Policy
* Academic Honesty Agreement

**Applies to**

* Students
* Staff (acknowledgement sometimes required)

**Notes**

* Often acknowledged per academic year
* Enforcement belongs elsewhere

---

### 5. **Conduct & Behaviour**

**Purpose:** Define expected behavior and consequences.

**Typical content**

* Student Code of Conduct
* Behaviour Management Policy
* Anti-Bullying Policy

**Applies to**

* Students
* Staff

**Notes**

* Must remain policy, not disciplinary tooling

---

### 6. **Health & Safety**

**Purpose:** Physical and medical safety obligations.

**Typical content**

* Health Disclosure & Consent
* Emergency Medical Treatment Consent
* Safety Procedures

**Applies to**

* Applicants
* Students
* Staff

**Notes**

* Often overlaps with admissions, but **category stays distinct**

---

### 7. **Operations**

**Purpose:** Institutional rules not tied to academics or safeguarding.

**Typical content**

* IT Acceptable Use Policy
* Facilities Use Policy
* Transportation Policy

**Applies to**

* Students
* Staff
* Guardians (contextual)

---

### 8. **Handbooks**

**Purpose:** Consolidated informational documents requiring acknowledgement.

**Typical content**

* Parent Handbook
* Student Handbook
* Staff Handbook

**Applies to**

* Guardians
* Students
* Staff

**Notes**

* A handbook is **not** a policy category workaround
* It can contain multiple policy references internally

---

### 9. **Employment**

**Purpose:** Employment-specific obligations.

**Typical content**

* Staff Code of Ethics
* Employment Terms Acknowledgement
* Workplace Conduct Policy

**Applies to**

* Staff only

---

## 2️⃣ Explicit Non-Categories (Forbidden)

These are **not allowed** as taxonomy entries:

❌ “Legal” (too broad)
❌ “Compliance” (outcome, not content)
❌ “Miscellaneous”
❌ “System”
❌ “Other”

If you need these, taxonomy is already broken.

---

## 3️⃣ Taxonomy Invariants (Locked Rules)

These rules are **non-negotiable**:

1. Every **Institutional Policy** has **exactly one category**
2. Categories do **not** imply enforcement
3. Categories do **not** encode lifecycle
4. Categories are **organization-wide**
5. Categories are **stable across schools**

---

## 4️⃣ How this plugs into what you already built

* `Institutional Policy.policy_category` → **this list**
* `Policy Version` → unaffected
* `Policy Acknowledgement` → unaffected
* Applicant readiness → reads **by policy applicability**, not category
* Staff / student / guardian flows → configured later

No refactor required.

---

## 5️⃣ Formal Lock Statement

> **Policy Taxonomy v1 is hereby locked.**
> Any new policy must map to one of the above categories.
> If it does not fit, policy content must be rewritten — not the system.

---
