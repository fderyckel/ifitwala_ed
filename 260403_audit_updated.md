# Updated Audit Report: Scalability, Caching, and Nested Scope Architecture
*Original: 2026-04-03 | Updated: 2026-04-14*

## Executive Summary
This audit continuation evaluates progress on the original 10 high-impact items. Status:
- **Critical (Impact 5/5)**: Item #1 (School Scope Violations) remains unresolved
- **High (Impact 4/5)**: Items #2, #7, #8, #9 need attention
- **Documentation**: Item #3 needs verification updates
- **Product/SPA**: Items #4, #5, #6 require product decisions before implementation

---

## 1. Exact-Match School Scope Violations in Reports (Impact: 5/5)
**Status**: ⚠️ **STILL UNRESOLVED** - Critical architectural defect

**Code Refs** (verified current state):
- `ifitwala_ed/students/report/case_entries_activity_log/case_entries_activity_log.py:183`
  ```python
  if f.get("school"):
      where.append("rc.school = %(school)s")  # Exact match - violates contract
  ```
- `ifitwala_ed/accounting/report/trial_balance/trial_balance.py:32`
  ```python
  if filters.get("school"):
      conditions.append("gl.school = %(school)s")  # Exact match
  ```
- `ifitwala_ed/accounting/report/aged_receivables/aged_receivables.py:43-45`
  ```python
  if filters.get("school"):
      conditions.append(
          "exists (select 1 from `tabSales Invoice Item` sii where sii.parent = si.name and sii.school = %(school)s)"
      )  # Exact match in EXISTS subquery
  ```
- `ifitwala_ed/accounting/report/student_attribution/student_attribution.py:59-61`
  ```python
  if filters.get("school"):
      conditions.append("sii.school = %(school)s")  # Exact match
  ```

**Required Fix Pattern** (from `enrollment_trend_report.py` - compliant implementation):
```python
from ifitwala_ed.utilities.school_tree import get_descendant_schools

# In execute() function:
school_filter = filters.get("school")
if school_filter:
    school_scope = tuple(get_descendant_schools(school_filter) or [school_filter])
    conditions.append("table.school IN %(school_scope)s")
    params["school_scope"] = school_scope
```

**Risk**: Breaks sibling-isolation models and obscures descendant-school data from parent-school administrators.

---

## 2. In-Process State & Missing Redis Layer Caching (Impact: 4/5)
**Status**: ⚠️ **STILL UNRESOLVED**

**Code Ref**: `ifitwala_ed/api/course_schedule.py:221-223`

Current implementation (Layer A - in-process only):
```python
schedule_cache: Dict[Tuple[str, str], Optional[str]] = {}
rotation_cache: Dict[Tuple[str, str], Dict[str, int]] = {}
term_cache: Dict[str, dict] = {}
```

These caches are instantiated per-request and discarded after. Per `caching_strategy.md`, "schedule resolution maps" are Category A targets requiring Redis with explicit invalidation.

**Required Changes**:
1. Replace dicts with `frappe.cache().get_value(key, generator=...)`
2. Use namespaced keys: `ifed:schedule:rot:{academic_year}:{school}`
3. Add invalidation hooks in `School Schedule Block`, `Student Group Schedule`, `Term` controllers

---

## 3. False Positives in `anti_patterns.md` (Impact: 2/5)
**Status**: 🔍 **NEEDS VERIFICATION & UPDATE**

Items 5, 6, 9, 10 still marked as "Observed from grep results" without resolution notes.

**Code Analysis**:
- Item 5 (`api/attendance.py:1611`): Uses aggregate SQL with `_compute_period_kpis` - appears resolved
- Item 6 (`program_enrollment.py:648`): Uses `_term_meta_many` batching - appears resolved
- Item 9 (`api/course_schedule.py:65`): Single lean SQL, not in loop - appears resolved
- Item 10 (`test_course_enrollment_tool.py`): Test patterns acceptable

**Action Required**: Update `anti_patterns.md` to mark these as "Resolved in current code" with verification notes.

---

## 4-6. Product/SPA Features (Impact: 5/5)
**Status**: 📋 **PRODUCT DECISION REQUIRED**

These require product/UX design decisions before engineering:
- #4: Student Hub / "Today Cockpit" - needs unified aggregation endpoint design
- #5: Unified Focus Routing - needs action_type enumeration finalization
- #6: Teaching Content Quick Create - needs curriculum fork logic specification

**SPA Code Location**: `ifitwala_ed/ui-spa/src/`
- Overlays: `ifitwala_ed/ui-spa/src/overlays/`
- Pages: `ifitwala_ed/ui-spa/src/pages/`
- Focus components exist: `FocusRouterOverlay.vue`, action components present

---

## 7. Transport Boundary & Contract Purity (Impact: 4/5)
**Status**: 🔍 **NEEDS AUDIT**

Location: `ifitwala_ed/ui-spa/src/types/contracts/` and `ifitwala_ed/ui-spa/src/resources/frappe.ts`

Need to verify:
- Type definitions don't inherit `{ message: T }` Frappe wrappers
- `response.data.message` unwrapping occurs only in `frappe.ts`
- Service hooks type against pure DTOs

---

## 8. Decouple UX Feedback from Overlay Lifecycle (Impact: 4/5)
**Status**: 🔍 **NEEDS AUDIT**

Location: `ifitwala_ed/ui-spa/src/overlays/` and `ifitwala_ed/ui-spa/src/lib/services/`

Need to verify:
- No `.refetch()` or `toast` calls inside overlays
- Services emit semantic signals only (`uiSignals.emit(SIGNAL_TODAY_INVALIDATE)`)
- Refresh owners handle UX responsibility

---

## 9. Calm-First Pedagogy Typography (Impact: 4/5)
**Status**: 🔍 **NEEDS AUDIT**

Locations:
- `ifitwala_ed/ui-spa/src/styles/components.css`
- `ifitwala_ed/ui-spa/src/pages/**/*.vue`

Need to verify:
- Uses CSS variables (`surface`) not raw hexes
- Typography uses canonical classes (`.type-body`, `.type-meta`)
- No `@apply` in scoped styles

---

## 10. Portal Navigation & Form Theming (Impact: 3/5)
**Status**: 🔍 **NEEDS AUDIT**

Locations:
- `ifitwala_ed/ui-spa/src/styles/app.css`
- `ifitwala_ed/ui-spa/src/components/PortalLayout.vue`
- `ifitwala_ed/ui-spa/src/components/PortalSidebar.vue`

Need to verify:
- No global input/select overrides
- Navigation centralized in PortalLayout/PortalSidebar
- State classes (`.portal-sidebar--expanded`) drive responsive behavior

---

## Priority Action Matrix

| Priority | Item | Effort | Risk if Deferred |
|----------|------|--------|------------------|
| P0 | #1 School Scope Violations | Medium | Data visibility bugs, permission leaks |
| P1 | #2 Redis Caching | Medium | Performance degradation at scale |
| P1 | #3 anti_patterns.md update | Low | Documentation drift |
| P2 | #7-10 SPA audits | Medium | UX inconsistency, tech debt |
| P3 | #4-6 Product features | High | Requires design decisions first |

---

## Detailed Fix Instructions for #1 (School Scope)

### For each report file:

**case_entries_activity_log.py**:
```python
# Add import at top
from ifitwala_ed.utilities.school_tree import get_descendant_schools

# In _build_where() function, replace:
# if f.get("school"):
#     where.append("rc.school = %(school)s")
#     params["school"] = f.school

# With:
if f.get("school"):
    school_scope = tuple(get_descendant_schools(f.school) or [f.school])
    where.append("rc.school IN %(school_scope)s")
    params["school_scope"] = school_scope
```

**trial_balance.py**:
```python
# Add import
from ifitwala_ed.utilities.school_tree import get_descendant_schools

# Replace lines 31-33:
# if filters.get("school"):
#     conditions.append("gl.school = %(school)s")
#     params.update({"school": filters.get("school")})

# With:
if filters.get("school"):
    school_scope = tuple(get_descendant_schools(filters.get("school")) or [filters.get("school")])
    conditions.append("gl.school IN %(school_scope)s")
    params["school_scope"] = school_scope
```

Similar pattern for `aged_receivables.py` and `student_attribution.py`.

---

## Files Requiring Changes

### Backend (High Priority)
1. `ifitwala_ed/students/report/case_entries_activity_log/case_entries_activity_log.py`
2. `ifitwala_ed/accounting/report/trial_balance/trial_balance.py`
3. `ifitwala_ed/accounting/report/aged_receivables/aged_receivables.py`
4. `ifitwala_ed/accounting/report/student_attribution/student_attribution.py`
5. `ifitwala_ed/api/course_schedule.py`
6. `ifitwala_ed/docs/anti_patterns.md`

### SPA (Medium Priority - Requires Product Decisions)
1. `ifitwala_ed/ui-spa/src/types/contracts/*.ts`
2. `ifitwala_ed/ui-spa/src/resources/frappe.ts`
3. `ifitwala_ed/ui-spa/src/overlays/**/*.vue`
4. `ifitwala_ed/ui-spa/src/styles/components.css`
5. `ifitwala_ed/ui-spa/src/styles/app.css`
6. `ifitwala_ed/ui-spa/src/components/PortalLayout.vue`

---

## Test Coverage Requirements

For school scope fixes, add tests following pattern from `test_attendance_report.py`:
```python
def test_report_includes_descendant_schools(self):
    """Verify that selecting a parent school includes descendant data."""
    # Create parent and child schools
    # Create records in both
    # Run report with parent school filter
    # Assert both parent and child records present
```

---

*Audit completed. Highest priority: Fix school scope violations (#1) as they represent active architectural defects affecting data visibility and permissions.*
