<!-- ifitwala_ed/docs/website/07_page_recipes.md -->
# Page Recipes (Current Baseline)

**Audience:** Marketing, admissions, and website managers
**Status (March 28, 2026):** Synced with implemented website editor and renderer behavior, including browse-first utility links, floating inquiry CTA, `section_carousel`, and public course catalog/detail surfaces
**Goal:** Low-friction page composition using currently supported blocks

---

## 0) Quick Rules

* One H1 owner block must be first (`hero`, `admissions_overview`, or `program_intro`).
* Route input for `School Website Page` is school-relative (`/`, `about`, `admissions`, `about/team`).
* Publication is workflow-driven (`Draft -> In Review -> Approved -> Published`) and website-owned records may also use `publish_at` / `expire_at`.
* First-time School publication now prepares and publishes canonical starter pages (`/`, `about`, `admissions`, `programs`) when the School itself is public.
* First-time Program/Course publication still prepares starter website/SEO defaults without bypassing profile review workflow.
* Allowed blocks depend on context:
  * `School Website Page` (Standard): `hero`, `rich_text`, `section_carousel`, `program_list`, `course_catalog`, `leadership`, `staff_directory`, `story_feed`, `academic_calendar`, `cta`, `faq`, `content_snippet`
  * `School Website Page` (Admissions): Standard + `admissions_overview`, `admissions_steps`, `admission_cta`
  * `Program Website Profile`: Standard + `program_intro`
  * `Course Website Profile`: Standard + `course_intro`, `learning_highlights`
  * `Website Story`: Standard blocks only
* Website shell utility actions are now first-class:
  * `Schools`
  * guest `Login`
  * authenticated `Hub` and `Logout`
  * floating `Let's Talk` bubble to inquiry route

---

## 1) Home Page Recipe (`route = /`)

Suggested block order:

1. `hero`
2. `rich_text`
3. `program_list`
4. `leadership` (optional)
5. `cta`

Example `hero` props:

```json
{
  "title": "Ifitwala Secondary School",
  "subtitle": "Home of the Brave",
  "images": [],
  "autoplay": true,
  "interval": 6000,
  "cta_label": "Book a Visit",
  "cta_link": "/apply/inquiry"
}
```

Example `program_list` props:

```json
{
  "school_scope": "current",
  "show_intro": true,
  "card_style": "standard",
  "limit": 6
}
```

Example `leadership` props:

```json
{
  "title": "Leadership & Administration",
  "description": "Meet the academic leaders and school professionals shaping learning each day.",
  "role_profiles": ["Academic Admin"],
  "limit": 4,
  "staff_limit": 8,
  "show_staff_carousel": true
}
```

---

## 2) About Page Recipe (`route = about`)

Suggested block order:

1. `hero`
2. `rich_text`
3. `section_carousel` (optional, repeatable)
4. `faq` (optional)
5. `leadership`
6. `cta`

Example `rich_text` props:

```json
{
  "content_html": "<h2>Our History</h2><p>Founded in 1998...</p><h2>Mission</h2><p>We build confident, compassionate learners.</p>",
  "max_width": "wide"
}
```

Example `section_carousel` props:

```json
{
  "heading": "Activities",
  "content_html": "<p>Students engage in arts, sports, and service throughout the year.</p>",
  "layout": "content_right",
  "items": [
    { "image": "/files/activity_01.jpg", "caption": "Athletics", "alt": "Students on field" },
    { "image": "/files/activity_02.jpg", "caption": "Creative arts", "alt": "Students in arts studio" }
  ],
  "autoplay": true,
  "interval": 5000,
  "cta_label": "Learn More",
  "cta_link": "/schools/iss/activities"
}
```

Notes for `leadership` on Home/About:

* By default the block renders `Academic Leadership` first, then `Faculty & Staff`.
* Both sections only include `Employee` records where `show_on_website = 1`.
* The primary carousel resolves from `Designation.default_role_profile = "Academic Admin"` unless page authors set a manual designation filter.
* If a parent-school page needs selected roles from child campuses, use `role_scopes` on the primary carousel and set an explicit `descendant_depth`; the secondary staff carousel remains exact-school.

---

## 3) Admissions Page Recipe (`route = admissions`, `page_type = Admissions`)

Suggested block order:

1. `admissions_overview` (H1 owner)
2. `rich_text`
3. `admissions_steps`
4. `faq`
5. one or more `admission_cta`
6. `content_snippet` (optional reuse)

Example `admissions_overview` props:

```json
{
  "heading": "Admissions",
  "content_html": "<p>Choosing a school is a major family decision. Our admissions experience is designed to feel personal, clear, and well paced from the very first step.</p><p>Families typically begin with an inquiry, continue with a conversation or campus visit when available, and then move into the application process with the support of the admissions team.</p>",
  "max_width": "wide"
}
```

Example `admissions_steps` props:

```json
{
  "steps": [
    { "key": "inquire", "title": "Inquire", "description": "Share a few details so the admissions team can understand your child and answer your questions.", "icon": "mail" },
    { "key": "visit", "title": "Visit", "description": "If visits or conversations are available, we will help your family experience the campus, culture, and learning environment.", "icon": "map" },
    { "key": "apply", "title": "Apply", "description": "Complete the application when you are ready, including any forms, records, and supporting materials.", "icon": "file-text" }
  ],
  "layout": "horizontal"
}
```

Example `admission_cta` props:

```json
{
  "intent": "inquire",
  "style": "primary",
  "label_override": "Get More Info",
  "icon": "mail"
}
```

Notes:

* Starter admissions pages now seed a richer editorial flow: overview, supporting copy, process steps, FAQs, then CTAs.
* The optional `visit` CTA is only seeded when `School.admissions_visit_route` is configured, so a brand-new public site does not crash on a missing visit target.
* Even if an older page still contains a `visit` CTA, runtime fallback now resolves it to the next viable admissions route instead of hard-failing the page render.

---

## 4) Program Profile Recipe (`Program Website Profile`)

Suggested block order:

1. `program_intro` (H1 owner)
2. `rich_text`
3. `faq` (optional)
4. `cta`

Example `program_intro` props:

```json
{
  "heading": "IB Diploma Programme",
  "content_html": "<p>A rigorous, globally recognized academic pathway.</p>",
  "cta_intent": "apply"
}
```

Notes:

* Profile `status` is derived from workflow state + school website readiness + program publish readiness + optional publish window.
* Assign `content_owner` when different teams share page ownership.
* Program page route is system-generated: `/schools/{school_slug}/programs/{program_slug}`.

---

## 5) Story Page Recipe (`Website Story`)

Suggested block order:

1. `hero`
2. `rich_text`
3. `content_snippet` (optional)
4. `cta` (optional)

Notes:

* `Website Story` uses the same validation rules for H1 ownership and block ordering.
* `content_owner` must be an enabled internal editor (`Marketing User`, `Website Manager`, or `System Manager`) in the relevant school scope; portal `Website User` accounts are not valid story owners.
* Story index route is handled at `/schools/{school_slug}/stories`.

---

## 6) Course Catalog Recipe (`route = courses`)

Suggested block order:

1. `hero`
2. `course_catalog`

Example `course_catalog` props:

```json
{
  "show_intro": true,
  "show_course_group": true,
  "show_related_programs": true,
  "card_style": "standard",
  "limit": 24
}
```

Notes:

* The route stays school-scoped: `/schools/{school_slug}/courses`.
* The page is system-seeded when the first published course profile is prepared for a school.

---

## 7) Course Profile Recipe (`Course Website Profile`)

Suggested block order:

1. `course_intro` (H1 owner)
2. `learning_highlights` (optional when curated rows exist)
3. `cta`

Example `course_intro` props:

```json
{
  "heading": "Biology HL",
  "cta_intent": "inquire"
}
```

Notes:

* `course_intro` renders the profile hero, intro, overview, aims, and assessment summary from the website profile fields.
* `learning_highlights` renders curated website-owned highlights, not a raw `Learning Unit` tree.
* Profile `status` is derived from workflow state + school website readiness + course publish readiness + optional publish window.
* Course page route is system-generated: `/schools/{school_slug}/courses/{course_slug}`.

---

## 8) Long-Scroll Feature Page Recipe (`route = experience` or `route = school-life`)

Suggested block order:

1. `hero`
2. `rich_text`
3. `section_carousel`
4. `section_carousel`
5. `section_carousel`
6. `cta`

Notes:

* Use alternating `layout` (`content_left`, `content_right`) for visual rhythm.
* Keep each section carousel to 2-5 images for clarity.
* Set `hero.image_fade_mode` + `hero.image_fade_opacity` to ensure heading contrast over full-width imagery.

---

## 9) Editor Workflow Recipe

For marketing collaboration:

1. Author saves as `Draft`.
2. Submit for review (`In Review`).
3. Reviewer marks `Approved`.
4. Publish (`Published`) after final check.

Minimum pre-publish checklist:

* one valid H1 owner block in first position
* meta title/description set
* at least one CTA for admissions, program, and course intent pages
* blocks valid for the current page context

---

## 10) Theme and Motion Recipe (D1/D2)

* Theme tokens are managed in `Website Theme Profile` (scope: School -> Organization -> Global).
* Motion enhancements are optional and non-critical:
  * shared: `/assets/ifitwala_ed/js/ifitwala_site.bundle.js`
  * block scripts: `hero`, `admission_cta`, `section_carousel`
* Content remains fully server-rendered and SEO-safe without JS.
