# Website Page Providers — Canonical Contracts (v1)

**Ifitwala_Ed — Proposal B**

> **Status:** Draft — pending sign-off
> **Authority:** Subordinate to
> • `website_architecture_proposal_b.md`
> • `website_blocks_registry.md`
> **Scope:** Public website only (unauthenticated)

---

## 0. Purpose of this document

This document defines the **only allowed data-access layer** for the website system.

A **Page Provider** is:

* trusted, app-owned Python code
* responsible for **fetching and shaping domain data**
* the *sole* source of dynamic data for blocks
* a strict replacement for:

  * Web Page `context_script`
  * Builder Data Scripts
  * Server Scripts

> Blocks never query data.
> Providers never render HTML.

---

## 1. Core Provider Principles (A+ Lock)

1. Providers live in **app code**, never in DB
2. Providers return **plain JSON-serializable dicts**
3. Providers are **read-only by default**
4. Providers define **stable contracts**
5. Blocks depend on providers — never the reverse
6. Providers may be cached aggressively
7. Providers may not execute tenant logic

---

## 2. Provider Taxonomy

Providers fall into three categories:

| Type                      | Description                          |
| ------------------------- | ------------------------------------ |
| **Page Providers**        | Build the full context for a route   |
| **Shared Data Providers** | Reusable domain fetchers             |
| **Derived Providers**     | Small helpers used by Page Providers |

Blocks consume **outputs**, not providers directly.

---

## 3. Page-Level Providers (Top-Level)

These correspond to actual routes.

---

### 3.1 `get_home_page_context`

**Used by**

* `/`
* `/home`

**Consumes**

* none (implicit default school or global context)

**Returns**

```json
{
  "hero_images": ImageSet[],
  "tagline": string,
  "school_stats": StatItem[],
  "featured_programs": ProgramCard[],
  "primary_cta": CtaObject
}
```

**Blocks fed**

* `hero_carousel`
* `tagline`
* `quick_stats`
* `program_grid`
* `primary_cta`

**Notes**

* No hard-coded school logic
* School resolution happens here, not in blocks

---

### 3.2 `get_school_page_context`

**Used by**

* `/schools/<school_slug>`

**Consumes**

```text
school_slug (required)
```

**Returns**

```json
{
  "school": SchoolSummary,
  "hero_images": ImageSet[],
  "philosophy_cards": CardItem[],
  "programs": ProgramCard[],
  "leadership": StaffProfile[],
  "staff": StaffProfile[],
  "primary_cta": CtaObject
}
```

**Blocks fed**

* `hero_carousel`
* `rich_cards_grid`
* `program_grid`
* `leadership_grid`
* `staff_carousel`
* `primary_cta`

**Critical rule**

> All filtering (department, featured, limits) happens here — never in blocks.

---

### 3.3 `get_program_page_context` (DEFERRED but defined)

**Used by**

* `/{school_slug}/programs/<program_slug>`

**Consumes**

```text
program_slug (required)
```

**Returns**

```json
{
  "program": ProgramDetail,
  "school": SchoolSummary,
  "overview": RichText,
  "curriculum": RichText,
  "outcomes": RichText,
  "cta": CtaObject
}
```

**Blocks fed**

* future `program_*` blocks

---

## 4. Shared Data Providers (Reusable)

These are **never routed directly**.

---

### 4.1 `get_school_stats`

**Returns**

```json
StatItem[] = {
  "label": string,
  "value": string
}
```

**Rules**

* Values are strings (formatted)
* No JS counters

---

### 4.2 `get_school_programs`

**Consumes**

```text
school
```

**Returns**

```json
ProgramCard[] = {
  "title": string,
  "url": string,
  "intro": string,
  "image": ImageRef
}
```

**Rules**

* Only programs with `Program Website Profile.status = "Published"`
* Program must satisfy `is_published = 1` and `archive = 0`
* Program must be offered by the school (Program Offering)
* Ordered by `is_featured desc`, then `lft asc`
* Intro truncated server-side
* Discoverability is school-scoped: navigation should expose a single `Programs` page (`School Website Page.route = "programs"`), and that page renders `program_list` cards that link to each program detail route.

---

### 4.3 `get_school_leadership`

**Consumes**

```text
school
```

**Returns**

```json
StaffProfile[] = {
  "name": string,
  "title": string,
  "photo": ImageRef,
  "bio": string
}
```

**Rules**

* Filtered by leadership roles
* Bio is plain text or sanitized HTML

---

### 4.4 `get_school_staff`

Same shape as leadership, different filter.

---

### 4.5 `get_school_hero_images`

**Returns**

```json
ImageSet[] = {
  "src_small": string,
  "src_medium": string,
  "src_large": string,
  "alt": string
}
```

**Rules**

* Uses existing `image_fallback.js` conventions
* No logic in templates

---

## 5. Derived / Helper Providers

Used internally only.

Examples:

* `truncate_text(text, length)`
* `resolve_school_from_slug(slug)`
* `build_image_set(file)`

These **never** return directly to blocks.

---

## 6. Provider ↔ Block Dependency Matrix

| Block           | Provider Output |
| --------------- | --------------- |
| hero_carousel   | `hero_images`   |
| tagline         | `tagline`       |
| quick_stats     | `school_stats`  |
| program_grid    | `programs`      |
| leadership_grid | `leadership`    |
| staff_carousel  | `staff`         |
| primary_cta     | `primary_cta`   |

This matrix is **authoritative**.

---

## 7. Caching Strategy (Design-Level)

| Provider                | Cache      |
| ----------------------- | ---------- |
| get_home_page_context   | short TTL  |
| get_school_page_context | medium TTL |
| shared providers        | long TTL   |

Caching is **transparent** to blocks.

---

## 8. Explicit Non-Capabilities

Providers must **never**:

* read request cookies
* inspect user session
* branch on roles
* execute dynamic imports
* run tenant logic
* mutate data

If a feature requires this, it does not belong on the public website.

---

## 9. Relationship to Builder

This document **replaces** Builder’s “Data Script” concept.

| Builder       | Ifitwala           |
| ------------- | ------------------ |
| Data Script   | Page Provider      |
| Script output | Provider contract  |
| Script editor | Code review        |
| Runtime trust | Compile-time trust |

---

## 10. Design Lock Statement

Once this document is approved:

* Server Scripts are obsolete for websites
* Web Page Python is banned
* Builder (if used) must bind only to these providers
* Any new block must declare its provider dependencies here

---

## 11. Next Logical Steps (After Approval)

1. Finalize provider contracts (this doc)
2. Define `School Website Page` DocType
3. Map current Web Pages → providers + blocks
4. Remove `context_script` entirely
5. Implement minimal renderer
6. Evaluate Builder UI integration safely

---
