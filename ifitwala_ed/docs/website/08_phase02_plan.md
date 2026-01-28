# PART 1 — Phase Ranking (What ships first vs later)

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
* `is_published`

### Routing

```
/{school_slug}/programs/{program_slug}
```

**Rules**

* Page exists if `is_published = 1`
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

1. Desk → **Program**
2. Open Program → Tab: **Website**
3. Toggle **“Publish on Website”**
4. Fill:

   * Intro
   * Hero
   * Blocks
   * SEO Profile
5. Save

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
  * is_published
  * hero_image
  * intro_text
  * blocks
  * seo_profile
* Auto-create on Program creation (optional)

**Output**

* Program pages become first-class marketing assets

---

### Step 7 — Program Routing & Listing

**Makes pages discoverable.**

**Tasks**

* Add route resolver:

  ```
  /{school_slug}/programs/{program_slug}
  ```
* Update Program List block:

  * Pull only published programs
  * Auto-link to detail pages

**Output**

* SEO-friendly program structure
* No manual linking

---

## PHASE 4 — Editor Experience (Friction removal)

### Step 8 — Preview & Safe Publishing

**Prevents marketing fear.**

**Tasks**

* Draft / Published states
* Preview tokenized URL
* Optional scheduled publish

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
  * scope (school / global)
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

* Only programs with `Program Website Profile.is_published = 1`
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
  * Last Updated
* Actions:

  * New Page
  * Preview
  * Publish

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

**Desk → Program → “Website” Tab**

Sections:

* Publish toggle
* Hero image
* Intro text
* Blocks
* SEO Profile

**CTA**

```
[✓] Publish on website
Route: /{school}/programs/{slug}
```

Marketing edits content.
ERP logic stays untouched.

---

## F. SEO Panel (Right Sidebar)

Always visible on page edit.

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

---

## G. Preview & Publish

**Top bar**

* Preview
* Save Draft
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






