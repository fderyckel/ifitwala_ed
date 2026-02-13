<!-- ifitwala_ed/docs/website/07_page_recipes.md -->
# Page Recipes (Current Baseline)

**Audience:** Marketing, admissions, and website managers  
**Status (February 12, 2026):** Synced with implemented website editor and renderer behavior  
**Goal:** Low-friction page composition using currently supported blocks

---

## 0) Quick Rules

* One H1 owner block must be first (`hero`, `admissions_overview`, or `program_intro`).
* Route input for `School Website Page` is school-relative (`/`, `about`, `admissions`, `about/team`).
* Publication is workflow-driven (`Draft -> In Review -> Approved -> Published`).
* Allowed blocks depend on context:
  * `School Website Page` (Standard): `hero`, `rich_text`, `program_list`, `leadership`, `cta`, `faq`, `content_snippet`
  * `School Website Page` (Admissions): Standard + `admissions_overview`, `admissions_steps`, `admission_cta`
  * `Program Website Profile`: Standard + `program_intro`
  * `Website Story`: Standard blocks only

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

---

## 2) About Page Recipe (`route = about`)

Suggested block order:

1. `hero`
2. `rich_text`
3. `leadership`
4. `faq` (optional)
5. `cta`

Example `rich_text` props:

```json
{
  "content_html": "<h2>Our History</h2><p>Founded in 1998...</p><h2>Mission</h2><p>We build confident, compassionate learners.</p>",
  "max_width": "wide"
}
```

---

## 3) Admissions Page Recipe (`route = admissions`, `page_type = Admissions`)

Suggested block order:

1. `admissions_overview` (H1 owner)
2. `admissions_steps`
3. `faq`
4. one or more `admission_cta`
5. `content_snippet` (optional reuse)

Example `admissions_overview` props:

```json
{
  "heading": "Admissions",
  "content_html": "<p>We welcome families who value curiosity, care, and growth.</p>",
  "max_width": "normal"
}
```

Example `admissions_steps` props:

```json
{
  "steps": [
    { "key": "inquire", "title": "Inquire", "description": "Start the conversation.", "icon": "mail" },
    { "key": "visit", "title": "Visit", "description": "Experience our campus.", "icon": "map" },
    { "key": "apply", "title": "Apply", "description": "Begin the application.", "icon": "file-text" }
  ],
  "layout": "horizontal"
}
```

Example `admission_cta` props:

```json
{
  "intent": "visit",
  "style": "primary",
  "label_override": "Book a Campus Visit"
}
```

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

* Profile `status` is derived from workflow state + program publish readiness.
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
* Story index route is handled at `/schools/{school_slug}/stories`.

---

## 6) Editor Workflow Recipe

For marketing collaboration:

1. Author saves as `Draft`.
2. Submit for review (`In Review`).
3. Reviewer marks `Approved`.
4. Publish (`Published`) after final check.

Minimum pre-publish checklist:

* one valid H1 owner block in first position
* meta title/description set
* at least one CTA for admissions and program intent pages
* blocks valid for the current page context

---

## 7) Theme and Motion Recipe (D1/D2)

* Theme tokens are managed in `Website Theme Profile` (scope: School -> Organization -> Global).
* Motion enhancements are optional and non-critical:
  * shared: `/assets/ifitwala_ed/js/ifitwala_site.bundle.js`
  * block scripts: `hero`, `admission_cta`
* Content remains fully server-rendered and SEO-safe without JS.
