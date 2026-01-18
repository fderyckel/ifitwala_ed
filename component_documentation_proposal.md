# Proposal: Component Documentation & Usage Identification

**Objective**: Add top-level comments to all components in `ui-spa/src/components/` to clearly identify their purpose and where they are used (Pages/Overlays).

## Proposed Documentation Standard

Every `.vue` file in `components/` must start with a comment block in this format:

```html
<!--
  [Component Name]
  [Brief Description]

  Used by:
  - [Page Name] (<path/to/page>)
  - [Overlay Name] (<path/to/overlay>)
-->
```

## Component Usage Map & Proposed Comments

### 1. Root Components

#### `CommentThreadDrawer.vue`
```html
<!--
  CommentThreadDrawer.vue
  Slide-out drawer for viewing and replying to comment threads on generic documents/communications.

  Used by:
  - MorningBriefing.vue (pages/staff/morning_brief)
  - OrgCommunicationArchive.vue (pages/staff)
-->
```

#### `ContentDialog.vue`
```html
<!--
  ContentDialog.vue
  A generic, high-z-index dialog for displaying rich HTML content (e.g., announcements, messages)
  directly via Teleport to body, often bypassing the standard OverlayHost stack.

  Used by:
  - MorningBriefing.vue (pages/staff/morning_brief)
-->
```

#### `PortalNavbar.vue`
```html
<!--
  PortalNavbar.vue
  Main top navigation bar for the Staff/Student portal layout. Handles user profile and mobile menu toggle.

  Used by:
  - PortalLayout.vue (layouts)
-->
```

### 2. Analytics Components (`components/analytics`)

#### `StatsTile.vue`
```html
<!--
  StatsTile.vue
  A presentation component for displaying a single key performance indicator (KPI) or statistic
  with an optional trend indicator and icon.

  Used by:
  - StudentLogAnalytics.vue (pages/staff/analytics)
  - RoomUtilization.vue (pages/staff/analytics)
  - InquiryAnalytics.vue (pages/staff/analytics)
-->
```

### 3. Calendar Components (`components/calendar`)

#### `ScheduleCalendar.vue`
```html
<!--
  ScheduleCalendar.vue
  FullCalendar wrapper for displaying staff or resource schedules. Handles event rendering and interaction.

  Used by:
  - StaffHome.vue (pages/staff)
-->
```

#### `StudentCalendar.vue`
```html
<!--
  StudentCalendar.vue
  FullCalendar wrapper specialized for the Student portal view, showing classes and school events.

  Used by:
  - PortalLayout.vue (or StudentHome.vue)
-->
```

### 4. Class Hub Components (`components/class-hub`)

#### `ClassHubHeader.vue`
```html
<!--
  ClassHubHeader.vue
  Sticky header for the Class Hub page. Displays the current class context (Subject, Grade)
  and session controls (Start/End Class).

  Used by:
  - ClassHub.vue (pages/staff)
-->
```

#### `StudentsGrid.vue`
```html
<!--
  StudentsGrid.vue
  The main grid view in Class Hub displaying student cards with status indicators (attendance, behavior).

  Used by:
  - ClassHub.vue (pages/staff)
-->
```

#### `MyTeachingPanel.vue`
```html
<!--
  MyTeachingPanel.vue
  Sidebar or panel in Class Hub showing the teacher's schedule/timetable for quick navigation between classes.

  Used by:
  - ClassHub.vue (pages/staff)
-->
```

### 5. Focus Components (`components/focus`)

#### `FocusListCard.vue`
```html
<!--
  FocusListCard.vue
  A dashboard card component that displays a summary or list of active Focus items (ToDos).

  Used by:
  - StaffHome.vue (pages/staff)
  - Focus page (if exists)
-->
```

#### `StudentLogFollowUpAction.vue`
```html
<!--
  StudentLogFollowUpAction.vue
  Action component (often in a router overlay) that allows a user to perform a follow-up action
  on a specific student log (e.g. resolve, reply).

  Used by:
  - FocusRouterOverlay.vue (overlays/focus)
-->
```

### 6. Filter Components (`components/filters`)

#### `DateRangePills.vue`
```html
<!--
  DateRangePills.vue
  A UI control for selecting common date ranges (Today, This Week, Last Month, etc.) via pill buttons.

  Used by:
  - InquiryAnalytics.vue (pages/staff/analytics)
  - OrgCommunicationArchive.vue (pages/staff)
-->
```

## Next Steps

1.  **Approval**: Confirm if this level of detail matches expectations.
2.  **Execution**: I will apply these comments to the top of each file.
3.  **Discovery**: For the remaining 30+ components not listed above, I will perform the same search-and-document process during execution.
