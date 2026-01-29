<!-- ifitwala_ed/docs/website/01_architecture_notes.md -->
# Website Architecture — Proposal B (A+ Canonical Design)

**Ifitwala_Ed — Website System v1**

> **Status:** Design-locked (pending explicit revision)
> **Scope:** Public marketing & information pages (School, Programs, Blog, Home)
> **Non-Goal:** LMS / Portal / authenticated app flows
> **Audience:** Core developers, system architects, security reviewers

---

## 0. Problem Statement (Why this exists)

Ifitwala_Ed requires a **flexible, live-updating website system** that allows:

* Per-school customization
* Rich layouts and content blocks
* Immediate reflection of data changes (programs, posts, staff)
* Safe operation in **multi-tenant environments**

Previous approaches (Frappe Web Page server scripts, embedded Python in DB) **violate isolation and security expectations** and introduce catastrophic failure modes (entire site blocked when scripts are disabled).

**Proposal B defines a Builder-inspired architecture that preserves flexibility without tenant-authored code execution.**

---

## 1. Core Architectural Principles (A+ Alignment)

These principles are **non-negotiable**.

### 1.1 No Tenant-Authored Code Execution

* ❌ No Python stored in DB
* ❌ No `context_script`
* ❌ No Server Scripts
* ❌ No Data Scripts
* ❌ No tenant JS execution

> The database stores **data only**, never executable logic.

---

### 1.2 Trusted Code vs Untrusted Data

* **Trusted:** App code (Python modules, templates, JS bundles)
* **Untrusted:** DocType content, JSON blocks, rich text

All execution happens in **trusted code paths only**.

---

### 1.3 Data-Driven Rendering (Not Static Builds)

* Pages are rendered **at request time**
* No static site rebuilds
* Changes in Programs / Blog / Staff reflect immediately

---

### 1.4 Same Contract Model as SPA

This system mirrors the SPA A+ rules:

| SPA               | Website        |
| ----------------- | -------------- |
| Service layer     | Page Provider  |
| Contracts         | Block schemas  |
| No UI logic in DB | No logic in DB |
| Typed payloads    | Validated JSON |

---

## 2. High-Level System Overview

```
HTTP Request
   ↓
Route Resolver
   ↓
Page Provider (trusted Python)
   ↓
Domain Data Fetch (School, Program, Blog, Staff)
   ↓
Render Context Assembly
   ↓
Block Renderer (Jinja or Vue)
   ↓
HTML Response
```

**Critical rule:**

> Providers may read data.
> Providers may not execute tenant logic.

---

## 3. Page Model (Builder-Lite)

### 3.1 Page as Data (Not Code)

Pages are stored as structured data:

```text
School Website Page
├─ route
├─ full_route
├─ school
├─ page_type
├─ blocks (JSON)
├─ published
└─ metadata
```

No executable fields exist.

---

### 3.2 Block-Based Composition

A page is an **ordered list of blocks**.

```json
{
  "type": "hero",
  "props": {
    "title": "A campus where curiosity blooms",
    "image": "hero.jpg"
  }
}
```

Blocks:

* Have a **known type**
* Have a **validated schema**
* Are rendered by **trusted templates**

---

## 4. Block Registry (Critical Safety Boundary)

### 4.1 App-Owned Block Registry

All block types are defined **in code**, not by users.

Each block definition includes:

* `block_type`
* `props_schema`
* `renderer`
* `allowed_data_sources`

> If a block is not registered, it cannot render.

---

### 4.2 Block Rendering Rules

* Rendering code lives in the app
* Blocks never execute logic
* Blocks receive **data**, not functions

---

## 5. Page Providers (Replacing Server Scripts)

### 5.1 What a Page Provider Is

A **Page Provider** is a trusted Python module that:

* Receives route parameters
* Fetches domain data
* Returns a render context

Example:

```python
def get_context(school_slug):
	return {
		"school": school,
		"programs": programs,
		"leaders": leaders,
	}
```

---

### 5.2 Provider Rules

* Must live in app code
* No dynamic imports
* No request mutation
* Read-only by default
* Cached where safe

Providers are the **only** place where data access logic exists.

---

## 6. Dynamic Data (Without Scripts)

### 6.1 Data Sources (Script Replacement)

Instead of scripts, blocks reference **named data sources**:

```json
{
  "type": "program_list",
  "data_source": "school_programs"
}
```

Mapping exists in app code:

```python
DATA_SOURCES = {
	"school_programs": get_school_programs,
}
```

---

### 6.2 Data Source Rules

* Pre-registered only
* App-owned functions
* No arbitrary queries
* No tenant configuration

This replaces **Builder Data Scripts** safely.

---

## 7. Assets & Frontend Strategy

### 7.1 Canonical Assets

* `website.css` (Tailwind entrypoint)
* `website.bundle.css` (build output)
* `website.js`
* `website.bundle.js` (build output)
* `image_fallback.js`

These are **authoritative** and reused across pages.

---

### 7.2 Styling Rules

* No inline JS
* CSS scoped by convention
* Custom CSS (if allowed) is scoped and sanitized
* Tailwind utilities only (no Bootstrap on public website pages)

---

## 8. Customization Model (What Schools Can Change)

### Allowed

* Text content
* Images
* Block ordering
* Block props
* Theme tokens (colors, spacing)
* Visibility toggles

### Forbidden

* Python
* JavaScript
* Queries
* Conditionals
* Loops
* Imports

This preserves **creative freedom without execution freedom**.

---

## 9. Security Model

### 9.1 Threats Explicitly Addressed

* Arbitrary code execution
* Cross-tenant data leaks
* Full-site outages due to script blocking
* Privilege escalation via scripts

---

### 9.2 Threats Explicitly Accepted

* Misconfigured content
* Poor layout decisions
* Excessive block usage (mitigated via UX)

---

## 10. Comparison to Frappe Builder

| Aspect         | Builder            | Proposal B  |
| -------------- | ------------------ | ----------- |
| Block model    | ✅                  | ✅           |
| Visual editor  | ✅                  | Planned     |
| Data scripts   | ✅                  | ❌           |
| Server scripts | Required           | Forbidden   |
| Tenant code    | Allowed            | Forbidden   |
| Trust model    | Site owner trusted | Tenant-safe |
| A+ compatible  | ❌                  | ✅           |

Proposal B **copies the architecture pattern**, not the trust assumption.

---

## 11. Explicit Design Decisions (Locked)

1. Server Scripts will **never** be enabled for websites.
2. No DB-stored Python will exist.
3. All dynamic data flows through Page Providers.
4. Blocks are data, not behavior.
5. Flexibility is achieved via configuration, not code.
6. The system must degrade gracefully (no hard 403 homepage failure).

Any future proposal violating these requires an explicit RFC.

---

## 12. Future-Proofing

This architecture allows:

* Gradual introduction of a visual editor
* Vue-based block renderers later
* Partial hydration if needed
* Migration to Builder-like UX without Builder-like risk

---

## 13. Non-Goals (Explicit)

* Competing with full CMS platforms
* Allowing tenant developers to “code”
* Supporting arbitrary page logic
* Replacing SPA routing

---

## 14. Final Position

Proposal B gives Ifitwala_Ed:

* Builder-level flexibility
* SPA-grade architectural rigor
* Multi-tenant safety
* Predictable operational behavior

This is **not a compromise**.
It is a deliberate architectural stance.

---






---

# Website Blocks Registry (v1)

**Ifitwala_Ed — Proposal B**

> **Status:** Draft — pending sign-off
> **Audience:** Core devs, frontend architects, content governance
> **Scope:** Public website blocks only (marketing & informational pages)
> **Non-goal:** Portal / LMS / authenticated experiences

---

## 0. Purpose of this document

This document defines the **canonical set of website blocks** supported by Ifitwala_Ed.

A **block** is:

* a composable unit of layout and meaning
* data-driven (never executable)
* rendered by trusted code
* safe for multi-tenant use
* SEO-aware by design

> If a feature is not representable as a block here, it does not exist on the website.

---

## 1. Design principles (applies to all blocks)

### 1.1 Data, not code

* Blocks contain **props**, never logic
* All data comes from **Page Providers**
* No conditionals, loops, or expressions in block config

---

### 1.2 SEO-first by default

Every block must:

* produce semantic HTML
* respect heading hierarchy (`h1`–`h6`)
* avoid duplicate H1s
* support alt text and metadata
* degrade gracefully without JS

---

### 1.3 Education website conventions (Finalsite-inspired)

Blocks should:

* emphasize clarity over cleverness
* privilege narrative (mission, values, people)
* avoid marketing gimmicks
* support multilingual content later

---

### 1.4 Accessibility baseline

* WCAG-aware markup
* keyboard navigable
* image alt required (or explicit opt-out)
* no text baked into images

---

## 2. Block lifecycle

Each block has:

* **Type** (string identifier)
* **Purpose** (why it exists)
* **Props schema** (validated JSON)
* **Data dependencies** (named sources)
* **SEO behavior**
* **Customization limits**

---

## 3. Canonical Blocks (v1)

Only blocks already needed by current school pages are included.

---

### 3.1 `hero`

**Purpose**
Primary narrative anchor for a page (identity, mission, positioning).

**Typical usage**

* Home page
* School landing page
* Program overview

**Props**

```json
{
  "title": "string (required)",
  "subtitle": "string (optional)",
  "image": "image reference (optional)",
  "cta_label": "string (optional)",
  "cta_link": "url (optional)"
}
```

**SEO**

* Renders a single `<h1>`
* Image requires alt text or decorative flag
* CTA rendered as `<a>`

**Customization limits**

* No arbitrary HTML
* No multiple CTAs (deliberate restraint)

---

### 3.2 `rich_text`

**Purpose**
Editorial content: philosophy, admissions notes, curriculum explanation.

**Props**

```json
{
  "content": "sanitized rich text",
  "heading_level": "h2|h3|h4 (default h2)"
}
```

**SEO**

* Headings explicitly controlled
* Content indexable
* No inline styles

**Notes**

* Uses your **clamped-text + expand** pattern by default

---

### 3.3 `quick_stats`

**Purpose**
High-level facts (years running, student count, ratios).

**Data source**

* `school_stats`

**Props**

```json
{
  "layout": "row|grid",
  "show_icons": true
}
```

**SEO**

* `<dl>` or semantic list
* Values rendered as text (not JS)

---

### 3.4 `program_list`

**Purpose**
Display academic offerings for a school.

**Data source**

* `school_programs` (published only)

**Props**

```json
{
  "layout": "grid|list",
  "show_age_range": true,
  "show_description": false
}
```

**SEO**

* Program titles as `<h3>`
* Each item links to canonical program page

**Notes**

* No filtering logic in block
* Filtering happens in provider only

---

### 3.5 `leadership_team`

**Purpose**
Present leadership (principal, coordinators).

**Data source**

* `school_leadership`

**Props**

```json
{
  "layout": "grid|carousel",
  "show_titles": true
}
```

**SEO**

* Names as headings
* Bios indexable text

---

### 3.6 `staff_grid`

**Purpose**
Show broader academic or administrative staff.

**Data source**

* `school_staff`

**Props**

```json
{
  "department": "optional filter",
  "layout": "grid"
}
```

**SEO**

* Primarily navigational
* Avoids overlong pages (provider caps count)

---

### 3.7 `image_gallery`

**Purpose**
Visual storytelling (campus, activities).

**Props**

```json
{
  "images": ["image references"],
  "layout": "grid|carousel"
}
```

**SEO**

* Every image requires alt text
* Lazy-loaded

---

### 3.8 `cta`

**Purpose**
Single, clear action (Apply, Visit, Contact).

**Props**

```json
{
  "title": "string",
  "description": "string",
  "cta_label": "string",
  "cta_link": "url"
}
```

**SEO**

* Text-based CTA
* No JS dependency

---

### 3.9 `faq`

**Purpose**
Answer common parent/student questions.

**Props**

```json
{
  "items": [
    { "question": "string", "answer": "rich text" }
  ]
}
```

**SEO**

* Schema.org FAQ markup (later enhancement)
* Collapsible but indexable

---

### 3.10 `blog_list`

**Purpose**
Show recent news, announcements.

**Data source**

* `school_blog_posts`

**Props**

```json
{
  "limit": 3,
  "show_excerpt": true
}
```

**SEO**

* Each post links to canonical blog page
* Titles rendered as headings

---

## 4. Explicitly forbidden blocks (v1)

These will **not** exist:

* `custom_html`
* `custom_js`
* `data_script`
* `code_block`
* `conditional_block`
* `loop_block`

> If you need these, the architecture has failed.

---

## 5. Rendering responsibilities

* Blocks are rendered by **trusted templates**
* No block renders raw user HTML without sanitization
* CSS/JS comes from canonical bundles only

---

## 6. Extensibility rules

Adding a new block requires:

1. Architecture review
2. Props schema definition
3. SEO and accessibility review
4. Provider data availability
5. Explicit inclusion in this registry

No ad-hoc blocks.

---

## 7. Alignment with Builder & Finalsite

| Aspect              | Builder | Finalsite | Ifitwala |
| ------------------- | ------- | --------- | -------- |
| Block-based         | ✅       | ✅         | ✅        |
| Visual editor       | ✅       | ✅         | Planned  |
| SEO focus           | ⚠️      | ✅         | ✅        |
| Tenant scripting    | ✅       | ❌         | ❌        |
| Education semantics | ⚠️      | ✅         | ✅        |
| Multi-tenant safe   | ❌       | N/A       | ✅        |

---

## 8. Design lock statement

This registry defines the **maximum expressive power** of the website system.

Any future feature:

* must fit inside this model, or
* must revise this document explicitly

---
