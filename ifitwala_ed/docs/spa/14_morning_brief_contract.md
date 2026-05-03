# Morning Brief Contract

> **Status:** Canonical
> **Audience:** Humans + AI agents
> **Scope:** Staff Morning Brief SPA surface, with emphasis on operational widgets that aggregate sensitive domains

This document records the locked behavior for the staff Morning Brief page where quick situational awareness crosses into permission-sensitive operational data.

If Morning Brief behavior changes, update this note with the code.

---

## 1. Core Page Rules

1. Morning Brief remains a bounded bootstrap surface: the page should initialize from one aggregated read endpoint wherever practical.
2. Morning Brief cards may summarize sensitive domains, but the SPA is never the permission boundary. Server endpoints own visibility.
3. Cards must fail clearly. If a card cannot resolve required context, the user must see why and what to fix next.
4. Drill-down overlays must preserve the context of the card that launched them instead of reopening in a different default mode.
5. Announcement attachments are drill-down detail, not page-bootstrap payload. The page may load governed attachment metadata only after the user opens a specific announcement.
6. Announcement drill-downs must reuse the Org Communication detail endpoint and governed attachment preview/open URLs. Morning Brief must not construct raw file paths or bypass the shared attachment preview contract.
7. Morning Brief announcement cards render directly in a responsive card grid, not a carousel plus secondary list. The grid is one column on smaller screens and two columns on wide screens; DOM order remains newest-first so visual reading order follows recency left-to-right, then top-to-bottom.
8. Morning Brief announcement ordering is newest first, oldest last. Priority remains a visual treatment only and must not override recency ordering on this surface.
9. Morning Brief bootstrap may include per-announcement `is_unread` state derived from the canonical Org Communication read-state model so the SPA can render read/unread without extra per-row calls.
10. Announcement detail headers must keep operational metadata quiet and scannable: the `Announcement` label and title share the first header row, while type, Morning Brief appearance window, and Desk link render as aligned metadata below the title rather than stacked labels.
11. Morning Brief announcement DTOs must include `brief_start_date` and `brief_end_date` so the modal can show the publish window without a second per-row lookup. The Desk link points to the same `Org Communication` record already authorized for the Morning Brief row.
12. Birthday widgets may show birthday icons and month/day labels, but staff-facing Morning Brief DTOs must not include raw student or employee date-of-birth fields.

---

## 2. Clinic Volume Card

### 2.1 Visibility

1. `clinic_volume` is visible only when the current user has server-side read access to `Student Patient Visit`.
2. This includes nurses and any other authorized role with that doctype permission.
3. The card must not be hard-coded to admin-only role checks in the SPA.

### 2.2 Scope

1. Clinic volume resolves from the current user's effective default school using canonical school-tree helpers.
2. If the selected/default school is a parent school, aggregation scope includes that school plus descendants.
3. Scope resolution must stay server-side and must not be recomputed ad hoc in the component.

### 2.3 Business Window Semantics

1. The card supports exactly two summary pills:
   - last 3 business days
   - last 3 business weeks
2. Business windows must exclude:
   - weekends from the resolved school calendar
   - school calendar holidays
3. The card must not count raw calendar days when a school calendar says the day is non-instructional.

### 2.4 Overlay / Trend Semantics

1. Opening clinic history must preserve the currently selected card window as the initial overlay range.
2. Clinic trend ranges must use the same business-day filtering contract as the card.
3. If school context is missing, the overlay must show an explicit actionable error instead of appearing stuck or indefinitely loading.

---

## 3. Concurrency Rules

1. Morning Brief page-init must not add a request waterfall for clinic volume range toggles; the card summary should switch locally from the bootstrap payload.
2. The clinic history overlay may fetch its own trend data on open, but the request must stay bounded by an explicit time range.
3. Weekend and holiday filtering must be derived from canonical calendar helpers, not from repeated per-row document loads.
4. Opening an announcement may trigger one bounded detail read for that announcement's body/attachments, but Morning Brief must not prefetch attachment DTOs for the whole announcement list.
5. Read/unread indicators for Morning Brief announcements must arrive in the bounded bootstrap payload; the SPA must not issue per-row read-state fetches.
6. The announcement Desk link and appearance window must be derived from the bounded bootstrap/detail state already in hand, not from an additional per-announcement request.

---

## 4. Canonical Code Refs

- `ifitwala_ed/api/morning_brief.py`
- `ifitwala_ed/ui-spa/src/pages/staff/morning_brief/MorningBriefing.vue`
- `ifitwala_ed/ui-spa/src/components/analytics/HistoryDialog.vue`
- `ifitwala_ed/ui-spa/src/types/morning_brief.ts`

## 5. Test Refs

- `ifitwala_ed/api/test_morning_brief.py`
- `ifitwala_ed/ui-spa/src/components/analytics/__tests__/HistoryDialog.test.ts`
