# PART 1 — Phase Ranking (What ships first vs later)

**Canonical implementation source:** `ifitwala_ed/website/block_registry.py` (block schemas and contracts)

### **Phase 1 (Foundational, must-have)**

These unlock real marketing autonomy immediately and compound SEO value.

1. Admissions Hub Page (structured)
2. Multi-CTA Admission Blocks (Inquire / Visit / Apply)
3. Program Detail Pages (auto-generated)
4. SEO Control Panel (per page)
5. FAQ Block (schema-ready)

**Why Phase 1**

* Covers 80% of real-world marketing needs
* Directly comparable to Finalsite
* Low conceptual risk
* Strong ERP ↔ CMS integration payoff

---

### **Phase 2 (Optimization & Scale)**

These improve efficiency, consistency, and SEO authority over time.

6. News / Stories Content Type
7. Reusable Content Blocks (snippets)
8. Media Library with Context Awareness
9. Internal Linking Assistant
10. Preview & Publishing Controls (advanced scheduling, etc.)

**Why Phase 2**

* Important, but not blocking day-to-day marketing
* Some require maturity in content volume
* Can be layered without refactors

---

# PART 2 — Top 5 Features

## Exact DocTypes + Block Specs (Concrete)

I am using **Frappe-native patterns** only: DocTypes, child tables, server rendering, light JS hydration.

---

## 1. Admissions Hub Page

### DocType: `Website Page`

(you already have this — we extend behavior, not schema explosion)

**Required fields**

* `page_type = Admissions`
* `school`
* `seo_profile` (Link)
* `blocks` (child table)

### New Block Types

* `Admissions Overview`
* `Admissions Steps`
* `Admissions FAQ`
* `Admissions CTA Group`
* `Admissions Contact`

Each is just a **block definition**, not a new page.

### Block: `Admissions Steps`

```json
{
  "type": "admissions_steps",
  "props": {
    "steps": [
      { "title": "Inquire", "description": "...", "icon": "mail" },
      { "title": "Visit", "description": "...", "icon": "map" },
      { "title": "Apply", "description": "...", "icon": "file-text" }
    ]
  }
}
```

**ERP integration**

* CTA links resolve to:

  * Inquiry form
  * Visit scheduling
  * Applicant portal
* CMS does **not** own the workflow — only the *entry points*

---

## 2. Multi-CTA Admission Blocks

### Block: `Admission CTA`

**Props**

```json
{
  "intent": "inquire | visit | apply",
  "label_override": null,
  "target": "internal",
  "style": "primary | secondary | outline"
}
```

**Why semantic**

* Marketing selects *intent*, not URL
* System resolves correct link based on:

  * School
  * Admissions configuration
  * Current availability

**Hydration**

* Minimal JS for hover state / analytics
* No Vue required

---

## 3. Program Detail Pages (Auto-Generated)

### DocType: `Program`

(already exists)

### New DocType: `Program Website Profile`

(1-to-1 with Program)

**Fields**

* `program`
* `hero_image`
* `intro_text`
* `blocks`
* `seo_profile`
* `workflow_state` (`Draft / In Review / Approved / Published`)
* `status` (Draft / Published, read-only, derived)

### Routing

```
/{school_slug}/programs/{program_slug}
```

**Rules**

* Page exists if `status = "Published"`
* Marketing edits *content*, not routing
* Program Offering logic stays out of CMS

---

## 4. SEO Control Panel

### DocType: `Website SEO Profile`

**Fields**

* `meta_title`
* `meta_description`
* `og_title`
* `og_description`
* `og_image`
* `canonical_url`
* `noindex` (checkbox)

**Attached to**

* Website Page
* Program Website Profile
* News / Story (Phase 2)

**Rendered server-side**

* Injected into `<head>`
* No JS dependency

---

## 5. FAQ Block (Schema-Ready)

### Block: `FAQ`

**Props**

```json
{
  "items": [
    { "question": "What curriculum do you offer?", "answer": "<p>...</p>" }
  ],
  "enable_schema": true
}
```

**Rendering**

* HTML for users
* JSON-LD injected if `enable_schema = true`

**Why this matters**

* Google rich results
* Marketing teams love FAQs
* Zero performance cost

---

# PART 3 — Editor UX Flows

## What a Marketing Manager Actually Clicks

This is the **most important part**.

---

## Flow A — Create / Edit Admissions Page

1. Desk → **Website Pages**
2. Click **“New Page”**
3. Select:

   * Page Type: `Admissions`
   * School
4. Page opens with **guided block scaffold**:

   * Overview
   * Steps
   * CTA Group
   * FAQ
5. Editor:

   * Edits text inline
   * Chooses CTA intent (no URLs)
   * Adds/removes FAQ items
6. Preview → Publish

**Zero code. Zero routing decisions. Zero broken links.**

---

## Flow B — Publish a Program Page

1. Desk → **Program Website Profile**
2. Create a new profile
3. Select School + Program
4. Fill:

   * Intro
   * Hero
   * Blocks (via main-form **Add Block** modal: pick block type, fill schema-guided props, click Add to insert row)
   * SEO Profile
5. Move Workflow State:

   * Request Review
   * Approve
   * Publish
6. Save

**Result**

* Program page appears automatically
* Program List block updates everywhere

---

## Flow C — Add CTA Anywhere

1. Edit any Website Page
2. Add Block → **Admission CTA**
3. Choose:

   * Intent: Inquire / Visit / Apply
   * Style
4. Done

**Marketing thinks in intent, not plumbing.**

---

## Flow D — SEO Check (No Guessing)

1. Open page
2. Side panel → **SEO Status**

   * Missing meta?
   * Multiple H1?
   * No OG image?
3. Fix inline

**Prevents silent SEO decay.**

---

## Flow E — Safe Preview & Publish

1. Click **Preview**
2. Share preview link internally
3. Publish or schedule

No broken live pages. No “oops” moments.

---

# UX / UI Design Principles (Locked)

* **Server-rendered HTML first** (SEO)
* **Tailwind only** (no inline CSS chaos)
* **Hydrate JS only where useful**
* **Vue only if interaction is complex** (e.g. internal linking assistant later)
* **No WYSIWYG free-for-all**
* **Editors choose intent, system resolves logic**

---

# Final Truth (Straight)

You are not building a “school website builder”.
You are building a **marketing surface that is natively aware of the ERP beneath it**.


---

# EXECUTION PLAN — CMS ENHANCEMENTS (10 FEATURES)

## Guiding execution rules (lock these first)

Before any code:

* No Vue unless interaction *cannot* be solved with light JS
* HTML must be server-rendered
* Blocks are **semantic**, not generic
* Editors choose **intent**, system resolves **logic**
* CMS never owns admissions workflow state

---

## PHASE 0 — Hard Locks (½ day, mandatory)

**Goal:** Prevent scope drift and future refactors.

1. **Freeze CMS boundaries**

   * Marketing CMS = discovery, persuasion, entry points
   * Admissions pipeline = Applicant + Portal only
   * No Applicant logic inside CMS blocks

2. **Confirm canonical page types**

   * Website Page
   * Program Website Profile
   * News / Story (Phase 2)

3. **Confirm rendering contract**

   * One renderer
   * One page template
   * Blocks render HTML only
   * Optional JS hydration per block

✅ *Exit condition:* Written confirmation + no open design questions

---

## PHASE 1 — Core Infrastructure (Foundation)

### Step 1 — SEO Control Panel (Global prerequisite)

**Why first:** Everything depends on this.

**Tasks**

* Create DocType: `Website SEO Profile`
* Fields:

  * meta_title
  * meta_description
  * og_title
  * og_description
  * og_image
  * canonical_url
  * noindex
* Attach to:

  * Website Page
  * Program Website Profile
* Inject into `<head>` in renderer

**Output**

* SEO is explicit, visible, enforceable

---

### Step 2 — Block Registry Finalization

**Why:** Prevents ad-hoc blocks later.

**Tasks**

* Lock block registry structure:

  * block_type
  * props_schema
  * template
  * optional JS
* Add validation:

  * Required props
  * Allowed values (e.g. CTA intent)

**Output**

* Predictable block behavior
* Safe editor experience

---

## PHASE 2 — Admissions Marketing (High-impact)

### Step 3 — Admission CTA Block (Atomic unit)

**Do this before pages.**

**Tasks**

* Define block: `admission_cta`
* Props:

  * intent: inquire | visit | apply
  * style
  * label_override (optional)
* Resolve target URL server-side via:

  * school
  * admissions settings
* Optional JS:

  * analytics click event

**Output**

* One CTA block usable everywhere
* Zero hardcoded URLs

---

### Step 4 — Admissions Hub Page (Composite)

**Uses CTA block internally.**

**Tasks**

* Extend Website Page:

  * page_type = Admissions
* Define block presets:

  * Admissions Overview
  * Admissions Steps
  * Admissions FAQ
  * CTA Group
* Add guided default layout on creation

**Output**

* Marketing can build full admissions pages without dev help

---

### Step 5 — FAQ Block (Schema-ready)

**SEO + UX win.**

**Tasks**

* Define block: `faq`
* Props:

  * items[{question, answer}]
  * enable_schema
* Render:

  * HTML list
  * JSON-LD if enabled

**Output**

* SEO rich results
* Reusable across pages

---

## PHASE 3 — Program Pages (SEO multiplier)

### Step 6 — Program Website Profile

**Bridges ERP ↔ CMS.**

**Tasks**

* Create DocType: `Program Website Profile`
* Fields:

  * program
  * workflow_state (Draft / In Review / Approved / Published, read-only in form; changed via actions)
  * status (Draft / Published, read-only; controlled by workflow + Program publish readiness)
  * hero_image
  * intro_text
  * blocks
  * seo_profile
* Auto-create on Program creation (optional)

**Output**

* Program pages become first-class marketing assets
* Visibility still governed by Program + Offering eligibility

---

### Step 7 — Program Routing & Listing

**Makes pages discoverable.**

**Tasks**

* Add route resolver:

  ```
  /{school_slug}/programs/{program_slug}
  ```
* Update Program List block:

  * Pull only published Program Website Profiles
  * Auto-link to detail pages
  * Require Program.is_published = 1 and Program.archive = 0
  * Require Program Offering for the school
* Guarantee school-level discoverability:

  * Ensure a `School Website Page` with route `programs` exists
  * Ensure that page is visible in navigation (`show_in_navigation = 1`)
  * Ensure that page includes a `program_list` block so cards are rendered without manual setup

**Output**

* SEO-friendly program structure
* No manual linking

---

## PHASE 4 — Editor Experience (Friction removal)

### Step 8 — Preview & Safe Publishing

**Prevents marketing fear.**

**Tasks**

* Workflow states: `Draft -> In Review -> Approved -> Published`
* Keep `status` read-only and derived from workflow + publish-readiness invariants
* Desk-only preview (`?preview=1`)
* No scheduling in Phase‑02

**Output**

* Confidence for editors
* Fewer mistakes

---

### Step 9 — Reusable Content Snippets

**Consistency at scale.**

**Tasks**

* Create DocType: `Website Snippet`
* Fields:

  * title
  * content
  * scope (school / organization / global)
* Snippet picker in Rich Text & blocks

**Output**

* No copy-paste drift
* Faster editing

---

## PHASE 5 — Authority & Scale (Phase 2 features)

### Step 10 — News / Stories Content Type

**Content freshness + storytelling.**

**Tasks**

* DocType: `Website Story`
* Fields:

  * title
  * content blocks
  * tags
  * seo_profile
  * publish_date
* Listing + detail pages
* Optional RSS

**Output**

* Competitor parity
* SEO freshness signals

---

## OPTIONAL (Later, not blocking)

* Internal linking assistant
* Media context tagging
* CTA conversion attribution dashboards

---

# FINAL EXECUTION ORDER (ONE-LINE CHECKLIST)

1. Lock CMS boundaries
2. Implement SEO Profile
3. Finalize block registry
4. Admission CTA block
5. Admissions Hub page
6. FAQ block
7. Program Website Profile
8. Program routing + list
9. Preview & publishing
10. News / Stories

---












# PART 1 — EXACT BLOCK JSON SCHEMAS (AUTHORITATIVE)

These schemas assume:

* `Website Page` has a child table `blocks`
* Each block row stores `{ block_type, props_json }`
* Validation happens server-side before render

---

## 1. `admission_cta` block

**Purpose:** Semantic admissions entry point (marketing intent, system resolves logic)

```json
{
  "block_type": "admission_cta",
  "props": {
    "intent": "inquire | visit | apply",
    "label_override": null,
    "style": "primary | secondary | outline",
    "icon": "mail | map | file-text | null",
    "tracking_id": null
  }
}
```

**Rules**

* `intent` is mandatory
* URL is resolved server-side based on:

  * school
  * admissions configuration
* `label_override` optional; default comes from intent
* `tracking_id` optional (future attribution)

---

## 2. `admissions_steps` block

**Purpose:** Visualize admissions journey without exposing workflow internals

```json
{
  "block_type": "admissions_steps",
  "props": {
    "steps": [
      {
        "key": "inquire",
        "title": "Inquire",
        "description": "Start the conversation with our admissions team.",
        "icon": "mail"
      },
      {
        "key": "visit",
        "title": "Visit",
        "description": "Experience our campus and community.",
        "icon": "map"
      },
      {
        "key": "apply",
        "title": "Apply",
        "description": "Begin the formal application process.",
        "icon": "file-text"
      }
    ],
    "layout": "horizontal | vertical"
  }
}
```

**Rules**

* `key` must match known intents
* Order is editor-controlled
* No workflow logic here (purely explanatory)

---

## 3. `admissions_overview` block

**Purpose:** High-level narrative framing

```json
{
  "block_type": "admissions_overview",
  "props": {
    "heading": "Admissions at Ifitwala",
    "content_html": "<p>We welcome families who...</p>",
    "max_width": "narrow | normal | wide"
  }
}
```

**Rules**

* Rich text allowed
* Editor controls width, not layout CSS

---

## 4. `faq` block (schema-ready)

**Purpose:** Parent friction removal + SEO

```json
{
  "block_type": "faq",
  "props": {
    "items": [
      {
        "question": "What curriculum do you offer?",
        "answer_html": "<p>We offer the IB continuum...</p>"
      },
      {
        "question": "Do you accept mid-year admissions?",
        "answer_html": "<p>Yes, subject to availability...</p>"
      }
    ],
    "enable_schema": true,
    "collapsed_by_default": true
  }
}
```

**Rules**

* If `enable_schema = true`, renderer injects JSON-LD
* No JS dependency required (details/summary or light JS toggle)

---

## 5. `program_list` block (already exists — tightened)

**Purpose:** Entry point into Program pages

```json
{
  "block_type": "program_list",
  "props": {
    "school_scope": "current | all",
    "show_intro": true,
    "card_style": "standard | compact",
    "limit": null
  }
}
```

**Rules**

* Only programs with `Program Website Profile.status = "Published"`
* Cards auto-link to program detail pages

---

## 6. `program_intro` block (Program detail page)

```json
{
  "block_type": "program_intro",
  "props": {
    "heading": "IB Diploma Programme",
    "content_html": "<p>The IB DP prepares students...</p>",
    "hero_image": "file_id",
    "cta_intent": "inquire | visit | apply | null"
  }
}
```

**Rules**

* Used only on Program pages
* CTA optional but semantic

---

## 7. `rich_text` block (already exists — governed)

```json
{
  "block_type": "rich_text",
  "props": {
    "content_html": "<p>...</p>",
    "max_width": "narrow | normal | wide"
  }
}
```

---

## 8. `content_snippet` block (Phase 2)

```json
{
  "block_type": "content_snippet",
  "props": {
    "snippet_id": "SNIPPET-NAME",
    "allow_override": false
  }
}
```

**Rules**

* Snippet content resolves server-side
* Prevents copy-paste drift

---

# PART 2 — DESK UI WIREFRAMES (MARKETING MANAGER VIEW)

These are **interaction-level wireframes**, not visuals — exactly what a UX designer or dev needs.

---

## A. Desk → Website Pages (Landing)

**Left sidebar**

* Website Pages
* Programs
* Stories / News (Phase 2)
* Media Library
* SEO Profiles

**Main panel**

* Table:

  * Title
  * Page Type (Admissions, Standard, Program)
  * School
  * Status (Draft / Published)
  * Workflow State (Draft / In Review / Approved / Published)
  * Last Updated
* Actions:

  * New Page
  * Preview
  * Request Review / Approve / Publish

---

## B. Create Admissions Page (Guided Flow)

**Step 1 — Modal**

```
Create New Page
[ ] Page Type: Admissions
[ ] School
[Create]
```

**Step 2 — Auto-scaffolded editor**
Blocks already present:

1. Admissions Overview
2. Admissions Steps
3. Admission CTA Group
4. FAQ

Editor can:

* Reorder blocks (drag)
* Edit inline
* Add CTA blocks without URLs

---

## C. Block Editor — Admission CTA

**Sidebar panel**

```
Admission CTA
--------------------
Intent:  (•) Inquire
         ( ) Visit
         ( ) Apply

Label override: [ optional ]
Style: [ Primary ▼ ]
Icon:  [ Auto ▼ ]

[ Save ]
```

**No URL field visible. Ever.**

---

## D. Block Editor — FAQ

**Repeating inline cards**

```
Q: [_____________________]
A: [ Rich text editor ]

[ + Add Question ]

[✓] Enable Google FAQ schema
```

---

## E. Program Website Editing Flow

**Desk → Program Website Profile**

Sections:

* School + Program
* Workflow State (Draft / In Review / Approved / Published)
* Status (Draft / Published, derived)
* Hero image
* Intro text
* Blocks
* SEO Profile

**Route**

```
/{school}/programs/{slug}
```

Marketing edits content without changing ERP logic.

---

## F. SEO Assistant Panel (Desk Headline)

Always visible on page edit (rendered in the Desk form headline area).

```
SEO Status
--------------------
✓ Meta title
✓ Meta description
⚠ No OG image
✓ Single H1
✓ Indexable

[ Edit SEO Profile ]
```

Editor action:

* `SEO Check` button refreshes warnings on demand.

---

## G. Preview & Publish

**Top bar**

* Preview
* Save Draft
* Request Review
* Approve
* Publish
* Schedule (Phase 2)

Preview opens:

* Server-rendered page
* Real URL with token

---

# WHY THIS WORKS (UX TRUTH)

Marketing managers:

* Think in **pages, programs, stories**
* Think in **intent, not URLs**
* Fear breaking SEO or admissions links
* Hate asking developers for small changes

This design:

* Removes all sharp edges
* Preserves ERP authority
* Keeps performance optimal
* Scales across schools cleanly

---

















# PART 1 — SERVER-SIDE VALIDATION RULES (AUTHORITATIVE)

These rules live **server-side only** (Document controllers / renderer validation).
UI validation is **assistive**, never authoritative.

---

## 1. Global Validation (All Website Pages)

### 1.1 Page-level invariants

**Applies to:** `Website Page`, `Program Website Profile`

**Rules**

* Exactly **one H1 per page**
* At least **one block**
* `school` must be set
* `seo_profile` is recommended; when missing, page-level fields are used as fallback
* Warn (do not block) if both SEO Profile and fallback fields are missing
* School must be public (is_published = 1 and website_slug set) for public rendering

**Hard failures**

```text
❌ Multiple H1 detected. Pages must contain exactly one H1.
❌ Website Page must be linked to a School.
❌ Website Page must contain at least one content block.
❌ School is not eligible for public website rendering.
```

---

## 1.2 Program Eligibility (Public Rendering)

**Applies to:** Program detail routes + Program List blocks

**Rules**

* Program must satisfy:
  * `is_published = 1`
  * `archive = 0`
  * `program_slug` set
* Program must be **offered by the school** (Program Offering)
* Program Website Profile must exist and be **Published**

**Failures (render‑time 404)**

```text
❌ Program not published or archived.
❌ Program not offered by this school.
❌ Program Website Profile not found or not published.
```

---

## 2. Block Registry Validation

### 2.1 Allowed block types (context-aware)

Only block types registered in the **Block Registry** may be saved, and each parent surface has a scoped allowlist.

```python
BASE_SURFACE_BLOCK_TYPES = {
  "hero",
  "rich_text",
  "program_list",
  "leadership",
  "cta",
  "faq",
  "content_snippet",
}

ADMISSIONS_SURFACE_BLOCK_TYPES = {
  "admissions_overview",
  "admissions_steps",
  "admission_cta",
}

PROGRAM_SURFACE_BLOCK_TYPES = {
  "program_intro",
}
```

Context resolution:

* `School Website Page` + `page_type = Standard` -> `BASE_SURFACE_BLOCK_TYPES`
* `School Website Page` + `page_type = Admissions` -> `BASE_SURFACE_BLOCK_TYPES + ADMISSIONS_SURFACE_BLOCK_TYPES`
* `Program Website Profile` -> `BASE_SURFACE_BLOCK_TYPES + PROGRAM_SURFACE_BLOCK_TYPES`
* `Website Story` -> `BASE_SURFACE_BLOCK_TYPES`

**Failure**

```text
❌ Unknown block type: {block_type}
❌ Block type(s) not allowed for {context}: {block_types}
```

---

## 3. `admission_cta` Validation

### Required fields

* `intent`

### Allowed values

```python
INTENTS = {"inquire", "visit", "apply"}
STYLES = {"primary", "secondary", "outline"}
```

### Rules

* `intent` is mandatory
* `intent` must be one of allowed values
* No URL field allowed (enforced by schema)
* Target URL is resolved server-side only

**Failures**

```text
❌ Admission CTA requires an intent.
❌ Invalid Admission CTA intent: {intent}
```

---

## 4. `admissions_steps` Validation

### Rules

* Must contain **at least 2 steps**
* Each step must include:

  * `key`
  * `title`
* `key` must match a known admission intent

```python
VALID_KEYS = {"inquire", "visit", "apply"}
```

**Failures**

```text
❌ Admissions Steps must include at least two steps.
❌ Invalid admissions step key: {key}
```

---

## 5. `faq` Validation

### Rules

* At least **1 FAQ item**
* Each item must have:

  * non-empty `question`
  * non-empty `answer_html`
* If `enable_schema = true`:

  * max **10 items** (Google guideline)

**Failures**

```text
❌ FAQ must contain at least one question.
❌ FAQ items require both question and answer.
❌ FAQ schema limited to 10 items.
```

---

## 6. `program_list` Validation

### Rules

* No manual program IDs allowed
* Programs resolved dynamically by:

  * `school_scope`
* `Program Website Profile.status = "Published"`

**Failure**

```text
❌ Program List cannot accept manually selected programs.
```

---

## 7. `program_intro` Validation

### Rules

* Only allowed on **Program pages**
* `heading` mandatory
* If `cta_intent` provided → must be valid admission intent

**Failures**

```text
❌ Program Intro block is only allowed on Program pages.
❌ Program Intro requires a heading.
❌ Invalid CTA intent on Program Intro.
```

---

## 8. `content_snippet` Validation

### Rules

* `snippet_id` must exist
* Snippet scope must be compatible:

  * global OR matching school
* `snippet_id` uniqueness is scope-aware:

  * unique per `(snippet_id, scope target)`
  * duplicate IDs are allowed across different schools/organizations

**Failures**

```text
❌ Content snippet not found.
❌ Content snippet not available for this school.
```

---

## 9. SEO Profile Validation

### Rules

* `meta_title` ≤ 60 chars
* `meta_description` ≤ 160 chars
* If `noindex = 1`:

  * warning banner shown in Desk (not a hard fail)

**Hard failures**

```text
❌ Meta title exceeds 60 characters.
❌ Meta description exceeds 160 characters.
```

---

## 10. Render-time Safety Checks (Non-blocking warnings)

Logged + surfaced in Desk sidebar:

* Missing OG image
* No FAQ schema on FAQ-heavy page
* Admissions page missing CTA
* Program page missing CTA

These **never block publishing**, but guide editors.

---

# PART 2 — TAILWIND LAYOUT CONVENTIONS (LOCKED)

These conventions ensure:

* Visual consistency
* Predictable spacing
* SEO-safe hierarchy
* Zero CSS drift

No block may define its own spacing system.

---

## GLOBAL PAGE WRAPPER

```html
<main class="page-content space-y-24">
```

* `space-y-24` is **canonical**
* No block overrides vertical rhythm

---

## 1. `admissions_overview`

```html
<section class="max-w-3xl mx-auto text-center space-y-6">
  <h1 class="text-4xl font-semibold tracking-tight">
  <div class="prose prose-lg mx-auto">
```

**Notes**

* Only block allowed to render `<h1>`
* Centered, calm, authoritative

---

## 2. `admissions_steps`

```html
<section class="max-w-6xl mx-auto grid gap-8 md:grid-cols-3">
  <div class="rounded-xl border p-6 text-center space-y-4">
```

* Cards must be equal height
* Icons use muted accent color
* No animation required

---

## 3. `admission_cta`

```html
<div class="flex justify-center">
  <a class="
    inline-flex items-center gap-2
    rounded-lg px-6 py-3
    text-sm font-medium
    transition
  ">
```

### Styles

* `primary` → `bg-slate-900 text-white hover:bg-slate-800`
* `secondary` → `bg-slate-100 text-slate-900 hover:bg-slate-200`
* `outline` → `border border-slate-300 hover:bg-slate-50`

---

## 4. `faq`

```html
<section class="max-w-4xl mx-auto divide-y">
  <details class="py-4">
    <summary class="font-medium cursor-pointer">
    <div class="prose mt-2">
```

* Use native `<details>` where possible
* Optional JS only for animation polish

---

## 5. `program_list`

```html
<section class="grid gap-8 md:grid-cols-3">
  <article class="rounded-xl border overflow-hidden">
```

* Cards must use:

  * same image ratio
  * same height
* Titles are `<h3>` only

---

## 6. `program_intro`

```html
<section class="max-w-4xl mx-auto space-y-6">
  <h1 class="text-4xl font-semibold">
  <div class="prose prose-lg">
```

* Program pages own their own `<h1>`
* Hero image always above text

---

## 7. `rich_text`

```html
<div class="prose max-w-none">
```

Width control:

* `narrow` → `max-w-2xl mx-auto`
* `normal` → `max-w-4xl mx-auto`
* `wide` → `max-w-6xl mx-auto`

---

## 8. `content_snippet`

```html
<div data-snippet class="contents">
```

* Snippet must not add wrappers
* Inherits layout from parent block

---

## FINAL LOCKED PRINCIPLES (DO NOT VIOLATE)

* No block defines global spacing
* No block injects inline styles
* No block sets fonts
* No block resolves URLs itself
* No block mutates ERP state
* Server validation > client validation
* SEO correctness > visual freedom

---
