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
