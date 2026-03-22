# 🌱 Ifitwala_Ed

### A Unified Institutional Operating System for Education

**Ifitwala_Ed** is an open-source **Institutional Operating System** that replaces fragmented SaaS tools with **one coherent data model, one permission system, and one analytics surface**.

Built on the enterprise-grade **Frappe Framework**, it is designed for schools, colleges, and universities that value **data sovereignty, architectural integrity, and long-term scalability.**

---

## 🚀 The Paradigm Shift

Most educational institutions operate on a "Frankenstein stack": an SIS for enrollment, an LMS for grading, a separate timetable tool, a HR module that is not connected to education, a Tableau dashboard for analytics, and endless spreadsheets to bridge the gaps.

**The result?** Data is duplicated, permissions drift, analytics require manual reconciliation, and staff waste time moving information instead of acting on it.

**Ifitwala_Ed eliminates fragmentation at the root.**
We do not build "integrations" between disconnected modules. We build **one backbone** where every module — Academic, Operational, HR, Marketing & Communication, and Financial — references the same single source of truth.

---

## 🏛️ Architecture: The Nested Set Hierarchy

Education is hierarchical by nature. Ifitwala Ed reflect this structure.

Ifitwala_Ed uses a **Nested Set Hierarchy** to model the reality of your institution. This is a lot more than just a labeling system; it is the logic engine that drives permissions, reporting, and policy inheritance throughout the whole system.

### Visualizing the Nested Reality

```mermaid
graph TD
    %% Nodes Definition
    ORG[🏢 Parent Organization]

    %% Level 1: Sub-Organizations
    SO1[🏫 Sub-Org 1: Standalone Primary]
    SO2[🎓 Sub-Org 2: Complex Schools Group]
    SO3[⚽ Sub-Org 3: Shared Facilities & Athletics]

    %% Level 2: Schools and Major Entities (Children of L1)
    SO1_PRI[🎒 Primary School]

    SO2_SEC[🏫 Secondary School]
    SO2_PRI[🏫 Primary School]
    SO2_LC[🧠 Learning Center]

    SO3_PLAY[🛝 Playground Complex]
    SO3_GOLF[⛳ Golf Center]
    SO3_GYM[🏟️ Athletic Center]

    %% Level 3: Sub-Divisions (Children of L2)
    SO2_HS[📜 High School]
    SO2_MS[📘 Middle School]

    SO2_UP[⬆️ Upper Primary]
    SO2_LP[⬇️ Lower Primary]
    SO2_KG[🧸 Kindergarten]

    SO2_TC[📝 Testing Center]

    %% Relationships Structure
    ORG --> SO1 & SO2 & SO3

    SO1 --> SO1_PRI

    SO2 --> SO2_SEC & SO2_PRI & SO2_LC
    SO2_SEC --> SO2_HS & SO2_MS
    SO2_PRI --> SO2_UP & SO2_LP & SO2_KG
    SO2_LC --> SO2_TC

    SO3 --> SO3_PLAY & SO3_GOLF & SO3_GYM

    %% Elegant Styling Definition
    classDef rootNode fill:#2E3B55,stroke:#1B263B,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef lvl1Node fill:#4A90E2,stroke:#357ABD,stroke-width:2px,color:#fff,rx:5px,ry:5px;
    classDef lvl2Node fill:#50C878,stroke:#3DAF65,stroke-width:1px,color:#fff,rx:5px,ry:5px;
    classDef lvl3Node fill:#A8E6CF,stroke:#8FD4BD,stroke-width:1px,color:#2E3B55,rx:5px,ry:5px;
    classDef facilityNode fill:#F7C548,stroke:#E1B137,stroke-width:1px,color:#2E3B55,rx:5px,ry:5px;

    %% Apply Styles
    class ORG rootNode;
    class SO1,SO2,SO3 lvl1Node;
    class SO1_PRI,SO2_SEC,SO2_PRI,SO2_LC lvl2Node;
    class SO2_HS,SO2_MS,SO2_UP,SO2_LP,SO2_KG,SO2_TC lvl3Node;
    class SO3_PLAY,SO3_GOLF,SO3_GYM facilityNode;
```

**Why this matters:**

1. **Inheritance:** A policy set at the `School` level automatically applies to all `Programs` within it.  A dashboard for a school applies to all the schools within it as well.
2. **Scoped Analytics:** A Head of Department sees data strictly for their node in the tree.
3. **Scalability:** The same system supports a single K-12 school or a multi-campus university group without re-architecture.

---

## 📅 The Time Engine: One Operational Reality

In most systems, the "Academic Timetable" and the "Administrative Calendar" are separate universes. This leads to double-bookings and invisible friction.

Ifitwala_Ed places teaching, meetings, exams, events, and maintenance on **One Shared Time Surface**.

### The "Fact Table" Guarantee

We determine availability via **Fact Tables**, not inferred patterns.

1. **Location Booking:** The single truth for room usage.
2. **Employee Booking:** The single truth for human time (Teaching + Meetings + Leaves).

> **The Rule:** If a record exists in the fact table, the resource is busy. The system prevents conflicts at the database level, ensuring utilization analytics are 100% accurate.

---

## 🎓 Academic Model: Separation of Concerns

We separate **Curriculum** (what we plan) from **Delivery** (what we teach) and **Assessment** (how we measure).

### 1. Curriculum Structure

`Program` → `Course` → `Learning Unit` → `Lesson`

* Curriculum is reusable and standards-friendly.
* It exists independently of the academic year.
* Academic year is educational scope only; accounting must use a separate fiscal year.

### 2. Assessment as a Mode

We treat assessment as a flexible mode of interaction, not a rigid category. The same task engine supports:

* **Binary Checks:** Complete/Incomplete.
* **Points:** Traditional grading.
* **Criteria/Rubrics:** Standards-based assessment.
* **Observation:** Qualitative logs.

### 3. Attendance as Data

Attendance is not a separate module. It is recorded against real **Teaching Events**. Once recorded, it flows immediately into student profiles, reports, and longitudinal analytics.

---

## 👥 One System, Multiple Experiences

In an educational institution, a Nurse, a Teacher, and a Registrar should never experience the software in the same way.

Ifitwala_Ed delivers **tailored perspectives** from the same backend:

| User | Experience | Focus |
| --- | --- | --- |
| **Academic Staff** | **Staff SPA** (Vue 3) | Streamlined for daily tasks: Attendance, Grading, Tasks. |
| **Students/Parents** | **Portals** | Read-only views for Schedules, Reports, and Homework. |
| **Admin/Ops** | **Desk Console** | Full access to Structure, HR, Assets, and Enrollment. |
| **Leadership** | **Analytics Dashboards** | Trends, Utilization, Financial Health. |

---

## 📣 Communication & Operations

### Precision Communication

Stop "reply-all" fatigue.

* **Targeted Audiences:** Message specific groups (e.g., "Grade 10 Parents" or "Science Faculty").
* **Morning Brief:** A daily digest that aggregates announcements relevant *only* to the user's role.
* **Traceability:** A full archive of who sent what, to whom, and when it was read.

### Health & Safeguarding

* **Isolation:** Medical records are structurally isolated.
* **Role-Gated:** Clinical details remain role-gated; aggregate Morning Brief clinic volume follows `Student Patient Visit` read permission.
* **Integrated Workflow:** If a student visits the nurse, the teacher is notified of the absence context without revealing sensitive details.

---

## 🔐 Security, Privacy, and Trust

Ifitwala_Ed relies on the battle-tested security foundations of the **Frappe Framework**.

* **Role-Based Access Control (RBAC):** Permissions are additive and contextual. A user can be a *Teacher* in the High School and a *Parent* in the Primary School simultaneously.
* **Field-Level Security:** Hide sensitive fields (e.g., Home Address) from general staff.
* **Audit Trails:** Every meaningful action—grade change, attendance modification, fee adjustment—is logged with a user timestamp.

---

## 🛠️ Technical Stack & Open Source Strategy

Ifitwala_Ed is **Open Source by design**. We believe institutions should own their infrastructure.

* **Backend:** [Frappe Framework](https://frappe.io) v16 (Python/MariaDB/Redis)
* **Frontend:** Vue 3, Tailwind CSS, Frappe UI
* **License:** GPL-3.0

### Why Self-Host?

1. **Data Sovereignty:** You own the database. You control the backups.
2. **Compliance:** Keep data within your national borders (GDPR, local regulations).
3. **Extensibility:** Extend the data model without waiting for a vendor roadmap.

---

## 🎯 Who is this for?

* **Schools & Colleges** tired of maintaining fragile integrations between 5+ systems.
* **Universities** requiring a flexible hierarchy for multi-faculty management.
* **IT Directors** who want clean, queryable SQL data and API access.
* **EdTech Consultants** looking for a serious, open-source alternative to legacy ERPs.

---

### 📬 Get in Touch

If you are exploring **modern, open, analytics-driven infrastructure for education**:

📧 **Email:** [f.deryckel@gmail.com](mailto:f.deryckel@gmail.com)

---

## ✅ Testing & CI

The repository includes a phased testing program with strict CI quality gates.

### Local backend smoke tests (bench)

```bash
bench --site <your-site> run-tests --app ifitwala_ed --module ifitwala_ed.schedule.test_enrollment_engine
bench --site <your-site> run-tests --app ifitwala_ed --module ifitwala_ed.schedule.doctype.program_enrollment_request.test_program_enrollment_request
bench --site <your-site> run-tests --app ifitwala_ed --module ifitwala_ed.api.test_guardian_home
```

### Local quality checks

```bash
ruff check .
bash scripts/contracts_guardrails.sh
bash scripts/test_metrics.sh
```

### Repo developer CLI (`codex`)

Use the repo-local wrapper to run CI-aligned commands:

```bash
./scripts/codex doctor
./scripts/codex lint
./scripts/codex backend-smoke --site <your-site>
./scripts/codex desk-build
./scripts/codex spa-typecheck
./scripts/codex ci --site <your-site>
```

Notes:
- `backend-smoke` runs the same default smoke modules as `.github/workflows/ci.yml`.
- `ci` runs lint + frontend checks + backend smoke unless skip flags are set.
- Use `--dry-run` to print commands without executing.

### Unified asset build (Desk + SPA)

```bash
yarn build
# bench build also triggers the same app build pipeline
```

Production source maps are disabled by default. Enable only for incident debugging:

```bash
IFITWALA_ASSET_SOURCEMAPS=1 yarn build:desk
```

### SPA checks

```bash
yarn type-check:spa
```

### Required PR checks

1. `backend-smoke`
2. `backend-domain`
3. `lint`
4. `desk-build`
5. `spa-typecheck-build`

Nightly heavy suites are defined separately in `.github/workflows/nightly.yml`.
