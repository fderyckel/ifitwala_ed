# Ifitwala_Ed — Standards-Based Grading (SBG) & Mastery Tracking Audit
*Target Equivalency: MasteryConnect (Instructure) / Top-Tier SBG Tools*

---

## Executive Summary

**ifitwala_ed** possesses a phenomenally well-thought-out foundation for standards-based grading out-of-the-box. By explicitly decoupling *Curriculum*, *Delivery*, and *Assessment Evidence* (via the 5-Layer Model), and by supporting a `Separate Criteria` scoring strategy at the Outcome level, the platform natively avoids the fatal flaws of traditional LMS gradebooks that force monolithic numeric grading.

However, to reach feature parity with market-leading mastery tracking tools like MasteryConnect, the system must bridge the gap between macro-level rubrics (`Assessment Criteria`) and micro-level standardized frameworks (`Learning Standards`). Furthermore, it must introduce standard-centric analytical layers (Mastery Trackers) that aggregate longitudinal data without violating the core Gradebook UX constraints established in `03_gradebook_notes.md`.

---

## 1. Current Architecture Strengths (What You Already Have)

Your current architecture natively supports the hardest structural paradigms of SBG. Traditional LMSs struggle because they treat a "Task" as a single column in a gradebook. Your architecture solves this.

### A. Decoupled Grading Strategies (`04_task_notes.md`)
The `default_rubric_scoring_strategy` supports `Separate Criteria`. This allows tasks to assess multiple dimensions without forcing a meaningless "Sum Total." In a true SBG environment, averaging a student's reading score with their formatting score corrupts the data. Your system explicitly protects per-criterion truth at the database level.

### B. Impeccable Evidence & Outcome Layers (The 5-Layer Model)
Unlike basic LMSs that destructively overwrite grades, your 5-layer per-student model (`Task` -> `Delivery` -> `Outcome` -> `Submission` -> `Contribution`) means you retain an auditable history of standard progression, peer-moderated judgments, and versioned evidence. `Task Outcome Criterion` correctly acts as the locked fact table for analytic queries.

### C. Planned Curriculum Primitives
The foundational semantic web for curriculum is present. The `Learning Standards` DocType is already built, capable of capturing standardized frameworks, strands, standard codes, and alignment types. `Learning Unit` and `Lesson` exist to structure these at the planning layer.

### D. Criteria & Performance Bands
`Assessment Criteria` and `Assessment Criteria Level` map perfectly to SBG rubrics (e.g., 1-4 scales for "Beginning" to "Exceeding"). This ensures qualitative grading is mathematically scalable and consistently applied across different assessors.

### E. Teacher-Centric UX Rules (`03_gradebook_notes.md`)
You have strictly defined that the primary grading view is *Delivery-centric*. This prevents the UI from becoming a convoluted, unusable matrix of standards during the rapid grading process.

---

## 2. Gap Analysis (What is Missing for MasteryConnect Parity)

To compete directly with tools like MasteryConnect, the platform lacks three major linkages and interfaces.

### A. The "Standard to Assessment" Linkage Gap
Currently, `Learning Standards` exist, and `Assessment Criteria` exist, but they are not explicitly linked at the assessment definition level.
* **MasteryConnect Feature:** Every question on a quiz or row on a rubric is directly tagged with a state/national standard.
* **ifitwala Gap:** `Assessment Criteria` (and by extension `Task Template Criterion`) lacks a child table to link to one or more `Learning Standards`. Without this, you cannot aggregate a student's performance on "CCSS.ELA-Literacy.RI.7.1" across multiple different tasks.

### B. The Mastery Tracking / Calculation Gap
Your current Gradebook aggregates live data per *Course × Student* (horizontal aggregation across deliveries). SBG requires aggregating live data per *Standard × Student* (vertical aggregation).
* **MasteryConnect Feature:** A visual "Mastery Tracker" (red/yellow/green) showing a student's current mastery level of a specific standard across the academic year. It calculates progress via sophisticated methods like *Decaying Average*, *Highest Score*, or *Power Law*.
* **ifitwala Gap:** There is currently no `Mastery Calculation Engine` or Standard-centric longitudinal view defined in the architecture.

### C. Micro-Assessment (Item Bank) Gap
* **MasteryConnect Feature:** Granular item banks where individual multiple-choice questions or sub-items are tagged to individual standards.
* **ifitwala Gap:** `Task` is currently a macro-level object (an assignment, project, or test). To perform micro-level standard tracking (e.g., Question 1 = Standard A, Question 2 = Standard B), you would need to treat each question as a `Task Template Criterion` or build an independent `Quiz` / `Item Bank` engine that behaves identically to the Criteria model in the backend.

---

## 3. Development Roadmap & Architectural Integration

To elevate ifitwala_ed to a top-tier SBG tool while respecting the existing architectural locks (specifically the fast UX constraints), you should execute the following phases:

### Phase 1: Link Criteria to Standards (Data Model Update)
*Constraint Checklist:* **Do not pollute the Task Delivery layer.** The standard mappings belong to the definition layers (`Assessment Criteria` or the Planned Curriculum).

1. **Update `Assessment Criteria`:** Add a child table `Aligned Standards` linking the criterion to `Learning Standards`.
2. **Update `Task Template Criterion`:** Allow teachers/curriculum designers to override or add `Learning Standards` at the Task definition level.
3. **Data Flow:** Because your `Task Outcome Criterion` pulls from these tables when a delivery is submitted/graded, any standard tagged here will automatically flow down to the official evidence table. This permits instantaneous analytics.

### Phase 2: The Mastery Calculation Engine (Backend Policy)
*Constraint Checklist:* An SBG calculation engine must read *only* from `Task Outcome Criterion` (adhering to the rule that UI/Analytics must trust Outcome + Outcome Criterion only).

1. **Create `Mastery Calculation Policy` DocType:** Let schools define how standard mastery is calculated mathematically (e.g., "Most Recent 3 Assessments", "Decaying Average 65/35", "Highest Score").
2. **Create `Standard Term Result` DocType:** Just as `Course Term Result` freezes the Gradebook at the reporting boundary, this will freeze a student's mastery level for specific standards at term-end, ensuring historical reporting stability.

### Phase 3: The "Mastery Tracker" Surface (Analytics View)
*Constraint Checklist:* Respecting the strict rule from `03_gradebook_notes.md` that the primary Gradebook is *Delivery-centric*, the Standard Tracker must be built as a separate, read-only analytical surface.

1. **Build the "Mastery Tracker" SPA View:**
   * **Rows:** Students.
   * **Columns:** Learning Standards (grouped by Strand/Substrand, collapsible).
   * **Cells:** Current calculated mastery level (color-coded based on `Assessment Criteria Level`).
   * **Click Action:** Clicking a cell opens a drawer showing the longitudinal timeline of `Task Outcomes` for that specific standard over the year.
2. **Strict UX Rule:** Teachers *cannot* grade from the Mastery Tracker. It is fundamentally an aggregator and visualizer.

### Phase 4: Accommodating Micro-Assessments (Quizzes / Item Banks)
If you want to support automated standards-based quizzes:
1. **Expand `Task` Grading Modes:** Add an `Item-Based` grading mode.
2. **Data Structure:** Instead of `Task Template Criterion`, use a `Task Item` child table where each row is a question linked to a standard.
3. **Execution:** The `Task Outcome` would store the results in a `Task Outcome Item` child table, which behaves identically to `Task Outcome Criterion` for the sake of standard-aggregation queries, allowing quizzes and rubrics to populate the identical Mastery Tracker.

---

## Conclusion

ifitwala_ed is 80% of the way to a true SBG powerhouse. Because you already did the grueling architectural work of separating **Outcome**, **Submission**, and **Contribution**, and because you natively support **Separate Criteria** scoring, adding MasteryConnect-style tracking is fundamentally a data-mapping exercise.

By mapping `Assessment Criteria` to `Learning Standards` (Phase 1) and building a read-only analytics surface on top of your existing `Task Outcome Criterion` fact table (Phase 3), you will unlock top-tier mastery tracking without slowing down the teacher's daily rapid-grading workflow.
