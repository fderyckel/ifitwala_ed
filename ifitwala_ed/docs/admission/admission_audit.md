# Admission Process Audit & Recommendations

**Date:** 2026-01-22
**Scope:** Phase 1, Phase 1.5, and Phase 2
**Status:** Work Completed until Phase 2

---

## 1. Audit Findings

### Phase 1 — Pipeline Wiring (Pass)
The core pipeline (`Inquiry` → `Student Applicant` → `Student`) is implemented with strict architectural integrity.

*   **Logic Enforcement:** `Student Applicant` strictly enforces status transitions. The `validate()` method correctly locks down `Organization`, `School`, and links to `Inquiry` and `Student`.
*   **Promotion Gate:** `Student.py` explicitly enforces the "only via promotion" rule. The `_validate_creation_source` method hard-blocks any Student creation that isn't from an Applicant (or explicit migration flag). This is a **strong implementation** ensuring data purity.
*   **Drift/Inefficiency:** None found. The implementation is lean and adheres to the plan.

### Phase 1.5 — Governance & Scoping (Partial Pass / Technical Debt)
The governance model (School/Organization scoping) is correctly anchored in `Student Applicant` fields and validated.

*   **Logic Enforcement:** Organization and School are required and immutable.
*   **Drift/Risk:** The Phase 1.5 plan explicitly states: **"Program Offering becomes the authoritative enrollment target."**
    *   **Current State:** `Student Applicant` logic relies on `program`, `academic_year`, and `term`. There is **no field** for `program_offering`.
    *   **Impact:** While the plan allows Phase 1.5 to be a "design lock", proceeding to Phase 2 (Intelligence) without a placeholder or path for `Program Offering` creates technical debt. Effectively, the "Targeting" is still conceptual (Program) rather than Contractual (Offering). This will require a schema migration later to enforce capacity and enrollment rules.

### Phase 2 — Admissions Intelligence (Pass with Note)
The "Intelligence" layer (Interviews, Health, Policies, Documents) is implemented with high fidelity to the "Meaning, not Mechanics" objective.

*   **Logic Enforcement:**
    *   **Interviews:** Correctly Staff-only.
    *   **Health:** Correctly staged (separate from `Student Patient`) and permission-gated.
    *   **Policies:** `Policy Acknowledgement` is strictly append-only, guardian-scoped, and version-aware.
    *   **Documents:** `Applicant Document` correctly handles routing contexts and reviews.
    *   **Readiness:** `get_readiness_snapshot` provides the required observability without premature automation.
*   **Drift/Inefficiency:**
    *   **"Hollow" Promotion:** Currently, `Student.after_insert` **skips** the creation of `User`, `Student Patient`, and `Contact` during promotion (via `from_applicant_promotion` flag).
        *   *Context:* This is technically correct for Phase 2 (checking "Phase 3 creates legal closure"), but it leaves the system in a state where a "Promoted" student is operationally non-functional until Phase 3 logic is written. This isn't "sloppy" but it is a **critical missing link** for end-to-end testing.

---

## 2. Recommendations for Top-Tier Admission Process

To separate Ifitwala_Ed from competitors and achieve "White Glove" operational excellence:

### 1. Dynamic "Smart" Readiness Engine (Top Tier Feature)
Currently, readiness is hardcoded (`has_required_policies`, etc.). A global-class system should allow Admissions Directors to configure **different readiness criteria** per Program/Grade.
*   *Why:* Applying for "Nursery" needs checking "Potty Training Policy", while "IB Diploma" needs "Transcript Review".
*   *Implementation:* Build a `Readiness Rule` doctype (Phase 2 extension) that dynamically injects checks into `get_readiness_snapshot`.

### 2. The "Applicant 360" Cockpit
Phase 2 adds data, but it's scattered in tabs. Build a unified **Admissions Cockpit** (Vue Component) for officers.
*   *Why:* Officers shouldn't click 4 tabs. They need a single view showing: *Timeline + Missing Items + Risk Flags + Interview Sentiment* side-by-side.
*   *Differentiation:* Competitors feel like databases (forms). Ifitwala_Ed should feel like a *decision support system*.

### 3. "Shadow" Enrollment via Program Offering
Close the Phase 1.5 gap immediately.
*   *Recommendation:* Add `program_offering` to `Student Applicant` now. When a `program` + `year` is selected, auto-resolve the valid `Program Offering` in the background.
*   *Differentiation:* This allows **Real-time Capacity Checks** during the application. If a seat fills up *while* they are applying, we can warn them. That is top-tier responsiveness.

### 4. Interactive "Missing Info" Loops
Don't just set status to "Missing Info".
*   *Recommendation:* When an Officer marks "Missing Info", require them to select *exactly which fields/docs* are missing. This generates a **precision token** for the family.
*   *Differentiation:* Instead of a generic "Check your application" email, the family gets a "Upload your Passport" magic link. Friction reduction = Higher conversion.

### 5. Multi-Round Interview Scorecards
Currently `Applicant Interview` is free-text notes.
*   *Recommendation:* Implement structured **Rubrics/Scorecards** for interviews (e.g., 1-5 scale on "Social Readiness", "Academic Potential").
*   *Differentiation:* Allows generating "Cohort Quality Heatmaps". Directors can see "This year's applicants index higher on Creativity".

### 6. Sibling & Alumni "Fast Track" Intelligence
Leverage the `Student` sibling logic during the *Application*.
*   *Recommendation:* Auto-detect if an applicant is a sibling of a current student (via Guardian matching). Flag them as "Community Family".
*   *Differentiation:* Give them a "Fast Track" visual badge. Recognizing existing families automatically creates a premium feeling of "We know you".

### 7. Admissions Forecasting (The "Yield" Metric)
Use the Phase 2 data to predict enrollment.
*   *Recommendation:* Add a `probability_score` (0-100%) to `Student Applicant`. Auto-calculate it based on "Time in Stage", "Interview Sentiment", and "Document Velocity".
*   *Differentiation:* Enable the CFO to see "Projected Revenue" based on *active funnel* not just *enrolled students*. This makes the system indispensable to Board Members, not just registrars.
