# Beck's System Knowledge — Ifitwala_Ed

## Architecture Overview

### SPA Architecture (A+ Model)
**Location:** `ifitwala_ed/ui-spa/`

**Core Ownership Rules:**
- **Pages** own refresh policy (subscribe to signals, decide when to refetch)
- **Services** own orchestration (API calls, emit invalidation signals after semantic success)
- **Overlays** own closing (immediate on success, no waiting for refresh/toast)
- **Server** owns all business logic and workflow truth

**Critical Invariants:**
- `types/` = contracts only (zero runtime code)
- `utils/` = pure stateless helpers
- `lib/` = runtime + services + orchestration
- One transport only: `createResource` via `resources/frappe.ts`
- No `fetch()` anywhere in SPA
- Transport envelope unwrapping happens ONLY in `resources/frappe.ts`
- Services return domain payloads only (never `{message: T}` unions)

**Folder Structure:**
```
ui-spa/src/
├─ pages/              # route-level views, refresh owners
├─ components/         # reusable UI components (NO overlays)
├─ overlays/           # workflow overlays via OverlayHost
├─ composables/        # shared reactive logic
├─ api/                # API wrappers (thin, legacy-compatible)
├─ types/contracts/    # TypeScript contracts only
├─ lib/services/       # UI services (API calls + signal emission)
├─ lib/uiSignals.ts    # invalidation bus
└─ utils/              # pure stateless helpers
```

**Overlay Rules:**
- Workflow overlays MUST be in `overlays/`, never `components/`
- On success: emit `close` immediately, then optionally `done(payload)`
- Never wait for refresh/toast/reload before closing
- Never emit signals or call refetch directly

**Naming Prohibitions:**
- Never use: `get_context`, `context`, `resolve_context`
- Use: `resolveXPayload`, `listXItems`, `submitX`

---

## Core Domain Models

### Academic Year
**File:** `docs/enrollment/academic_year_architecture.md`

- School-scoped (tree-aware: parent selection includes descendants)
- Lifecycle-governed (`archived`, `visible_to_admission`)
- **Never inferred from dates** — always explicit
- Retirement via End of Year Checklist (scoped executor, not global SQL)

### Student Log
**File:** `docs/student/student_log_docs.md`

3-layer observational workflow:
1. **Recording** — frictionless capture (attendance context, staff home)
2. **Showing** — Morning Briefing integration, analytics dashboard
3. **Follow-up** — explicit routing to assignee, Focus integration, closes the loop

Key: Original note locks once follow-up begins. Focus routes tasks. No black holes.

### Admissions
**File:** `docs/admission/01_governance.md`

**Pipeline:** `Inquiry → Student Applicant → Promotion → Student`

- Student **cannot exist** except through Applicant promotion
- **Institutional anchoring mandatory:** every Applicant has explicit `organization` + `school`
- Program Offering (not Program) is the operational authority
- Requirements are local, lifecycle is global
- Admissions files owned by Student Applicant (never Student/Guardian)

### Files & Documents
**File:** `docs/files_and_policies/files_01_architecture_notes.md`

- **File ≠ Business Document**
- Dispatcher-only uploads (no direct `File.insert()`)
- Slot-based storage: `profile_photo`, `contract`, `submission`, etc.
- `File Classification` Doctype (1:1 with File) for GDPR
- Primary subject + secondary subjects model
- Deterministic folder structure: `/{ORG}/{SCHOOL}/{DOMAIN}/{ENTITY}/{SLOT}/`

### Assessment
**File:** `docs/assessment/01_assessment_notes.md`

**Layered primitives:**
- Assessment Category → semantic grouping (Formative/Summative)
- Assessment Criteria → what is assessed (curriculum artifact)
- Assessment Criteria Levels → performance bands
- Grade Scale → numeric to symbolic conversion (institutional policy)
- Task → evidence intent
- Delivery → context for grading
- Task Outcome → official per-student result
- Gradebook → live aggregation (analytical only)
- Course Term Result → frozen institutional truth

**Rule:** Tasks provide evidence only. Never compute final grades.

### Employee Booking
**File:** `docs/scheduling/employee_booking_notes.md`

- Employee availability truth (datetime-first)
- Created from: Teaching (materialized), Meetings, School Events
- `blocks_availability` flag — critical for conflict logic
- Upsert-then-delete pattern (never delete-all-recreate)
- Canonical overlap: `from_datetime < end AND to_datetime > start`

---

## Data Integrity Rules

### Permission Model
- School-tree scoped (ancestors/descendants)
- Explicit anchoring required
- No inference chains

### GDPR Compliance
- Data subject classification mandatory
- Retention policies machine-readable
- Erasure workflow (not function call)
- Crypto-erase ready (key destruction)

### Migration Safety
- Never rename fields casually
- Never delete without migration strategy
- Never change types without data preservation
- School-scoped operations only (no global SQL updates)

---

## Development Workflow

**Before Coding:**
1. Check `/docs/engineering/` for related notes (Documentation-First Protocol)
2. Read current feature issue/PR
3. Confirm contract types in `types/contracts/`
4. Verify no naming collisions with framework

**Implementation:**
1. Write/update tests first
2. Server-side logic (DocType events, controllers)
3. UI Services for SPA
4. Overlays for workflows
5. Update engineering docs if behavior changed

**PR Requirements:**
- Link to Issue
- Tests pass
- Engineering docs updated
- Document which docs were consulted

---

## Key Anti-Patterns (Forbidden)

- Date math as authority ("current year from date")
- Global SQL updates without school scoping
- Business logic in Vue components
- Overlay depending on refresh to close
- Service showing toasts
- Direct `File.insert()` without dispatcher
- `fetch()` in SPA
- Runtime code in `types/`
- Transport unwrapping outside `resources/frappe.ts`

---

## Module Directory Mapping

```
ifitwala_ed/
├─ admission/          # Inquiry → Applicant → Student pipeline
├─ assessment/         # Tasks, criteria, grading, gradebook
├─ curriculum/         # Programs, courses, criteria banks
├─ enrollment/         # Academic Year, Program Enrollment
├─ files_and_policies/ # File Classification, retention, GDPR
├─ health/             # Medical records, vaccinations
├─ hr/                 # Employees, contracts
├─ schedule/           # Timetables, bookings, teaching materialization
├─ school_settings/    # Schools, orgs, academic structure
├─ students/           # Student, Student Log, guardians
├─ ui-spa/             # Vue 3 SPA (A+ architecture)
└─ website/            # Public site, portals
```

---

## Lessons from Issue #8 (Guardian Login Redirect)

### Debugging Process Applied

**Problem Pattern:** Feature exists (Guardian portal, SPA routing, API) but behavior fails at integration boundary (login).

**Diagnostic Steps:**
1. Read issue → understood expected: Guardian → `/portal/guardian/`
2. Traced login flow: `after_login` hook in hooks.py → `redirect_user_to_entry_portal()` in api/users.py
3. Identified missing case: Guardians not handled in redirect function
4. Verified SPA routing would work: `index.py` sets `defaultPortal = "guardian"` when Guardian role detected
5. Confirmed Guardian role assignment works in `guardian.py::create_guardian_user()`

**Root Cause Categories:**
- Integration gap: Core feature built, but login hook missed
- Priority ordering: Students checked before Guardians (correct: Student takes precedence)
- No fallback: Others fell through to Desk defaults

---

### Key Architectural Discoveries

#### Login Routing Stack
```
User logs in
    ↓
Frappe calls after_login hook
    ↓
ifitwala_ed.api.users.redirect_user_to_entry_portal()
    ↓
Role-based switch → sets frappe.local.response["home_page"]
    ↓
Browser loads /portal (or /sp, /admissions, etc.)
    ↓
index.py renders template with window.defaultPortal
    ↓
Vue router reads defaultPortal → redirects to guardian-home
```

**Critical Fields:**
- `User.home_page` — persistent preference (set on first redirect, respected thereafter)
- `frappe.local.response["home_page"]` — immediate redirect for this request
- `window.defaultPortal` — SPA routing hint (set by server based on roles)

#### Priority Order (Locked)
1. Student → `/sp` (always, highest priority)
2. Guardian → `/portal` (SPA routes to guardian-home)
3. Employee → `/portal/staff` (respects explicit /app opt-in)
4. Admissions Applicant → `/admissions`
5. Others → Desk defaults

**Why this order matters:**
- Students must always see student portal (even if also Guardians)
- Guardians should see family view before staff view (if dual-role)
- Employees can opt-in to Desk via explicit home_page setting

---

### Code Patterns for Auth Routing

**The `_force_redirect()` Pattern:**
```python
def _force_redirect(path: str, also_set_home_page: bool = True):
    if also_set_home_page:
        frappe.db.set_value("User", user, "home_page", path)
    frappe.local.response["home_page"] = path
    frappe.local.response["redirect_to"] = path
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = path
```

**Respecting User Choice:**
```python
current_home = (frappe.db.get_value("User", user, "home_page") or "").strip()
if not current_home:
    _force_redirect("/portal", also_set_home_page=True)  # First time
else:
    if current_home in ("/portal", "/portal/guardian"):
        _force_redirect(current_home, also_set_home_page=False)  # Known portal path
    # Else: respect their explicit choice, don't redirect
```

**Role Detection:**
- Use `frappe.get_roles(user)` for role list
- Use `frappe.db.exists("DocType", {"link_field": user})` for doc-type-based identity
- Student: `Student.student_user_id`
- Guardian: `Guardian.user`
- Employee: `Employee.user_id` + `employment_status = "Active"`

---

### Testing Strategy

**Test Patterns for Login Redirects:**
1. Create user with specific role
2. Create linked doc (Guardian, Student, etc.)
3. `frappe.set_user(email)` to simulate login
4. Clear `frappe.local.response` before call
5. Call redirect function
6. Assert on response keys and user.home_page
7. Cleanup: set back to Administrator, delete test docs

**Critical Assertions:**
```python
self.assertEqual(frappe.local.response.get("home_page"), "/portal")
self.assertEqual(frappe.local.response.get("type"), "redirect")
user.reload()
self.assertEqual(user.home_page, "/portal")
```

---

### Common Pitfalls (Learned)

1. **Silent fallthrough:** Missing a role case causes Desk default (confusing UX)
2. **Overwriting user choice:** Always check existing `home_page` before setting
3. **Wrong role detection:** Using only `frappe.db.exists()` without role check can miss inactive records
4. **SPA vs server routing mismatch:** Server sends to `/portal`, SPA reads `defaultPortal` to pick actual route
5. **Test cleanup:** Not resetting `frappe.set_user("Administrator")` leaves session polluted

---

### Documentation Discipline

For auth/routing changes, document:
- Priority order (explicit table)
- Integration flow (diagram or step list)
- Configuration fields that control behavior
- Test coverage requirements
- Backwards compatibility considerations

Location: `/docs/spa/` for SPA-visible routing, `/docs/engineering/` for backend logic
