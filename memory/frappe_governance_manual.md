# Ifitwala_Ed Frappe Reality Manual
## A Governance-Grade Handbook for Coding Agents

**Status:** Authoritative | **Scope:** Frappe Framework, Vue SPA, Production Systems

---

## 0) Operating Constitution (Non-negotiable)

### 0.1 Execution Flow
1. **Plan** — state the change, files touched, risks
2. **Green-light** — explicit scope approval
3. **Execute** — one focused step

### 0.2 Scope Discipline
- One problem at a time
- One file at a time (unless change requires multiple)
- Never propose refactors without current authoritative file
- **Never output partial method implementations** — Full method bodies only

### 0.3 Authority of Artifacts
- Any file user uploads is authoritative going forward
- Any file text I output that user applies becomes new authoritative version
- Never re-issue older versions

---

## PART I — FRAPPE MENTAL MODEL

### 1. DocTypes Are Contracts, Not Tables

A DocType defines:
- **Ownership** — source of truth
- **Lifecycle** — draft → submitted → archived/retired/closed
- **Scope** — org/school/AY
- **Governance semantics** — who can do what, for whom, under what authority

**Rule:** If it matters for governance, audit, permissions, or institutional correctness → enforce server-side.

**Common Failure Modes:**
- Putting lifecycle logic in Web Pages
- Patching missing rules in client JS
- "Fixing" governance by adding fields to File

### 2. Controllers Are "Law"

DocType JSON provides structure and UI hints. **Enforcement lives in Python controllers:**
- `validate()` = invariants and governance enforcement
- `before_save()` = derive fields / normalize values
- `after_insert()` / `on_update()` / `on_submit()` = side effects, notifications, ToDos, comments

**Rule:** Don't treat UI config as enforcement.

---

## PART II — GOVERNANCE: IDENTITY, AUTHORITY, ACTOR

### 2.1 Authority ≠ Identity ≠ Actor

| Concept | Meaning | Example |
|---------|---------|---------|
| User | Authentication (who clicked) | f.deryckel@gmail.com |
| Guardian/Student/Applicant/Employee | Organizational/legal roles (who policy is for) | "Parent of Student X" |

**Pattern:**
- Store who policy is for (`acknowledged_for`)
- Store context (`context_doctype`, `context_name`)
- Validate actor eligibility in Python

### 2.2 Never Infer Legal Relationships

**Resist:**
- Overloading single field for multiple relationships
- Treating uploads as consent evidence
- Treating "applicant_user" as "guardian"

**Rule:** If relationship matters legally/operationally → deserves own DocType/child table.

### 2.3 Phased Governance Is Correctness

Use explicit phases (Phase 1/2/3) to avoid:
- Retroactive inference
- Silent behavior changes
- Breaking historical data

**Rule:** Document limitations instead of "papering over" with assumptions.

---

## PART III — SINGLES: CONTROL SURFACES ONLY

### 3.1 Single DocType ≠ Global Authority

**Singles are best for:**
- Defaults
- Toggles
- Bootstrap flags
- Control surfaces for coordinated actions

**Not for:**
- Ledgers
- History storage
- Scoped (school-aware) configuration
- Publishing/routing authorities

**Rule:** If it must be school-aware, publish-aware, CMS-driven, or lifecycle-scoped → does not belong in Single.

---

## PART IV — HIERARCHY AND SCOPE (Multi-school Reality)

### 4.1 "Global" Defaults Are Latent Bugs

In hierarchical system (Org → Schools → …):
- Any "global action" must resolve scope explicitly
- Destructive operations must never rely on implicit global scope

**Rule:** If tree exists, every destructive operation must resolve scope intentionally.

### 4.2 Centralize Hierarchy Resolution

Parent/descendant resolution must be implemented once and reused everywhere.
Default school per user reduces cognitive overhead and permission mistakes.

**Rule:** Never "filter by link fields only" when hierarchy exists; always resolve scope.

---

## PART V — STATE BEATS INFERENCE

### 5.1 Consumers Read State; Never Infer Lifecycle

"Past academic year" determined by dates is brittle.

**Explicit flags/status:**
- `visible_to_admission`
- `archived`
- `status = Active/Retired`

**Rule:** Explicit state is only reliable lifecycle signal.

### 5.2 Prefer Existing Lifecycle Semantics

If doctype already has `status = Active/Retired`, don't invent parallel "archived" system.

**Rule:** Reuse existing lifecycle semantics before inventing new ones.

---

## PART VI — CLIENT FILTERS ARE UX, NOT GOVERNANCE

### 6.1 frm.set_query() Is Advisory

Improves editor experience but does not enforce policy.

**Rule:** If violating it would be governance problem → enforce in Python.

### 6.2 The Last set_query() Wins (Silently)

Multiple `set_query()` declarations for same field across onload/school/refresh will override silently.

**Rule:** One field → one canonical query definition.

### 6.3 Server Queries Ignore Client Filters

If Link field uses `query=...`, all constraints must be enforced there; client-side filters are irrelevant.

**Rule:** Server query is the law.

---

## PART VII — SCHEMA DRIFT: MOST DANGEROUS BUG CLASS

### 7.1 SQL Is a Schema Contract

If you reference column in SQL and schema changes (renamed/removed), Frappe will not save you — crashes at runtime.

**Example failure:** SQL referenced removed column → crashed form refresh.

**Rule:** Any raw SQL must be audited whenever models evolve.

### 7.2 Optional/Global Fields Must Be Handled Explicitly

If field is "leave empty for global", SQL that does `field IN (scope)` will exclude NULL/global rows.

**Rule:** If NULL is meaningful by design, every query must explicitly include it.

### 7.3 Fix Crashes Before "UI Weirdness"

One exception during refresh can poison entire form lifecycle and make unrelated UI appear broken.

**Rule:** Eliminate refresh crashes first; UI symptoms often mask backend exceptions.

---

## PART VIII — LAYERED ENFORCEMENT

### 8.1 Validation Duplication Is Acceptable

When layers differ:
- UI: guidance
- Save: enforcement
- Lifecycle/API: protection against misuse

**Rule:** Duplication is bad; layered enforcement is good when responsibilities differ.

---

## PART IX — TIME IS GOVERNANCE PROBLEM

### 9.1 Frappe Time Field Returns timedelta

Treat it as contract, not surprise.

**Locked rule:** Time-like coercion must support:
- `datetime.timedelta`
- `datetime.time`
- `datetime.datetime`
- `strings`

**Must be centralized** in `_coerce_time()` or equivalent. No ad-hoc parsing.

### 9.2 Sorting By Display Time Is Wrong

Sort by real datetime (SQL ORDER BY / hidden column), display as hh:mm.

### 9.3 No Silent Schedule Resolution Failures

If core context exists but block/location cannot be resolved:
- Return structured debug payload or log
- Do not silently return nulls

**Rule:** Silent failure is forbidden.

---

## PART X — FILES ARE GOVERNED DATA

### 10.1 Frappe File Is Transport, Not Governance

File = path + linkage. Governance must live in explicit policy (classification, retention, purpose).

### 10.2 is_private ≠ Compliance

Private storage is access control, not governance. Governance requires lawful basis, purpose, retention, accountability.

### 10.3 Attach Image Is Not Finished State

Attach creates File and dumps it somewhere; governance must:
- Intercept
- Re-slot
- Classify
- Cleanup original
- Avoid orphans/duplicates

### 10.4 Proven Operational Pattern

Authoritative pattern: `rename_student_image()`:
- Create folders under Home
- Rename/move
- Update File correctly
- Sync relevant image fields
- Avoid duplication

**Rule:** File operations are lifecycle events; treat them like governance actions.

---

## PART XI — HOOKS VS CONTROLLERS

### 11.1 Prefer Document Controllers

Hooks hide behavior and increase drift. Controllers keep logic close to model.

**Rule:** If logic belongs to DocType lifecycle → belongs in Document class.

---

## PART XII — SERVER RENDERING VS SPA

### 12.1 Server-Rendered HTML Is Strategic Advantage

Deterministic rendering improves:
- SEO
- Performance
- Governance clarity
- Predictability

JS should be additive; Vue used where interaction complexity demands it.

### 12.2 Desk vs Portal SPA Boundaries

- **Desk:** Bootstrap 5; keep Desk-first for classic reports
- **Portal SPA:** Vue 3 + Tailwind + frappe-ui
- **Tailwind must be scoped** to avoid leaking into Desk

---

## PART XIII — CMS AND ROUTING GOVERNANCE

### 13.1 Identity ≠ Content ≠ Presentation

| Layer | Responsibility |
|-------|---------------|
| Core DocTypes | Identity/state (School, Program) |
| CMS DocTypes | Content/intent (Website Pages, Blocks) |
| Renderer | Composition & safety |
| Templates | Presentation only |

**Rule:** Presentation layers must not own identity/routing decisions.

### 13.2 Deterministic Routing (Derived, Not Typed)

Editors never type full URLs.
Canonical routes computed via resolver (`school_slug + page.route → full_route`).

**Rule:** If URL can be derived, it must not be editable.

### 13.3 Semantic Blocks, Not Generic Blobs

Blocks encode intent; props are:
- Explicit
- Flat
- Schema-validated
- Editor-safe

**Nested JSON "flexibility" is rejected.**

### 13.4 Navigation Is Site Chrome

Navbar belongs to renderer shell populated from published pages (`show_in_navigation`, ordering). Not Website Settings, not per-page blocks.

### 13.5 "Fail Loudly in Desk, Fail Safely in Public"

- No silent fallbacks that mask errors
- On public site, safe outcomes (e.g., 404) preferable to incorrect renders

---

## PART XIV — INTEROPERABILITY

### 14.1 Single Source of Truth

Treat standards (OneRoster, etc.) as:
- External interoperability adapters
- Border translation layers

**Never** as internal data model authorities.

**Rule:** Be interoperable without being defined by interoperability.

---

## PART XV — ADMIN ACTIONS

### 15.1 Buttons Must Be Safe to Click Twice

End-of-year actions, closures, bulk operations must:
- Be re-runnable
- Not corrupt state
- Handle partial completion safely

**Rule:** Any admin action must be idempotent.

---

## PART XVI — CODING AGENTS: WHAT BREAKS, WHAT SCALES

### 16.1 Agents Default to "Make It Work"

They will:
- Infer relationships
- Reuse fields for new meanings
- "Finish the system" prematurely

**Rule:** Constrain agents by explicit contracts and phase boundaries.

### 16.2 One PR = One Concept

Avoid bundling unrelated changes. Linear sequencing prevents drift.

### 16.3 Green-Lights Must Be Explicit

Approval is contract, not vibe.

### 16.4 Never Let Agents Invent Abstractions

Framework-agnostic patterns often conflict with Frappe idioms.

### 16.5 Full Context or No Debugging

Provide full files and tracebacks; snippets produce confident but incomplete fixes.

### 16.6 Tracebacks Beat Intent

Always start from traceback. Don't lead with theories.

### 16.7 Agents Need "Context Lenses"

Different agent roles:
- PM agent reads friction, doesn't code
- Engineer agent must read architecture notes before edits
- Audit agent must propose fixes, not just critique

### 16.8 Silent Failures Are Unacceptable

Returning None, catch-and-ignore, unlogged fallbacks: **forbidden**.

---

## PART XVII — HARD RULES CHECKLIST (Agent Gate)

Before any change, confirm:

### Schema & Model
- [ ] I have current DocType schema / authoritative files
- [ ] I am not guessing fieldnames
- [ ] Any SQL touched was audited for schema drift and NULL semantics

### Governance
- [ ] Any rule that matters is enforced server-side
- [ ] Authority/actor separation is preserved
- [ ] Scope is explicit (school/org/AY). No implicit global operations

### UX & Surfaces
- [ ] Desk vs SPA boundaries respected
- [ ] Tailwind scoping preserved
- [ ] Overlays/services/pages respect side-effect ownership rules

### Reliability
- [ ] No silent fallback behavior
- [ ] Crashers removed before UI debugging
- [ ] Admin actions are idempotent

---

## META PRINCIPLE

> **Clarity beats cleverness.**
> **Explicit contracts beat implicit assumptions.**
> **Governance beats convenience.**

You are not building CRUD. You are encoding institutional authority, lifecycle, and accountability into software.

---

## APPENDIX — QUICK REFERENCE CARD

### Permission Debugging
```python
# Clear cache first
frappe.cache().flushall()

# Check actual permissions
frappe.has_permission("DocType", "read", docname, user)

# Check roles
frappe.get_roles(user)
```

### Safe SQL Patterns
```python
# Always handle NULL explicitly
filters = [
    ["school", "in", schools],
    ["school", "is", "not set"]  # Include global
]

# Never overwrite filter dict keys
filters = {"status": "Active"}
filters["status"] = "Draft"  # WRONG - lost Active

# Use lists for complex filters
filters = [["status", "=", "Active"], ["date", ">=", start_date]]
```

### Controller Patterns
```python
def validate(self):
    # Invariants and governance
    pass

def before_save(self):
    # Derive fields / normalize
    pass

def after_insert(self):
    # Side effects, notifications
    pass

def on_submit(self):
    # Final state changes
    pass
```

### File Governance Pattern
```python
def process_upload(self):
    # 1. Intercept
    # 2. Classify
    # 3. Re-slot to correct folder
    # 4. Update File record
    # 5. Cleanup original
    # 6. Log governance action
    pass
```

### Time Coercion
```python
def _coerce_time(value):
    """Support: timedelta, time, datetime, strings"""
    if isinstance(value, timedelta):
        hours = int(value.total_seconds() // 3600)
        mins = int((value.total_seconds() % 3600) // 60)
        return f"{hours:02d}:{mins:02d}"
    # ... other cases
```

### Guardian/Actor Pattern
```python
# Store who policy is for
self.acknowledged_for = student
self.context_doctype = "Student"
self.context_name = student

# Validate actor eligibility
if not frappe.has_permission("Student", "read", self.acknowledged_for):
    frappe.throw(_("Not authorized for this student"))
```

### Link Field Query Pattern
```python
def get_query():
    return {
        "filters": {
            "status": "Active",
            "school": ["in", get_user_schools()]
        }
    }
```
