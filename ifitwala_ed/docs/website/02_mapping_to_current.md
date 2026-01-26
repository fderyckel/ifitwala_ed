# Part 1 — What you already have (decoded)

From `web_page.json` and the shared assets, I see **three real pages**:

1. `home`
2. `school` (dynamic)
3. `program` (dynamic shell, mostly empty)

Even though they are written as raw Web Pages, **they are already block-composed in practice**.

Let’s name them.

---

## Page: `home`

### 1. **Hero Carousel Block**

**Where**

* Jinja loop over `school.gallery_image`
* CSS: `.hero-slide`, `.hero-img-wrapper`
* JS: carousel init + progressive image load

**This is a block. Period.**

**Canonical name**

```
hero_carousel
```

**Props (implicit today)**

* images[] { src_small, src_medium, src_large, caption }
* autoplay (hardcoded)
* transition (fade)

**SEO**

* ✅ image alt support
* ⚠️ caption not semantic yet
* ⚠️ no `<h1>` inside hero

---

### 2. **Tagline Block**

**Where**

```jinja
{% if school.school_tagline %}
<div class="school-tagline">{{ school.school_tagline }}</div>
{% endif %}
```

**Canonical name**

```
tagline
```

**Notes**

* This should *own* the `<h1>` for SEO
* Currently it is styled text, not semantic

---

## Page: `school` (dynamic, heavy)

This page is *rich*, and clearly block-based already.

---

### 3. **Hero Image Carousel (variant)**

Same as `home`, but with:

* WebP pipeline
* preload
* caption overlay position variants

**Canonical block**

```
hero_carousel
```

**Variant**

```
variant = "school"
```

---

### 4. **Philosophy Cards Grid**

**Where**

* Splitting HTML by `<h2>`
* Rendering 3-column cards
* Clamp + expand behavior

**This is fragile as hell today — but conceptually sound.**

**Canonical block**

```
rich_cards_grid
```

**Props**

* title
* cards[] { title, html, icon }

**SEO**

* ⚠️ content split via string parsing (bad)
* ✅ headings present
* Needs structured source (DocType field → child table)

---

### 5. **Academic Programs Grid**

**Where**

* `Program` query
* `is_featured`
* Card layout + CTA

**Canonical block**

```
program_grid
```

**Props**

* school
* limit
* featured_first
* show_cta

**SEO**

* ✅ internal links
* ⚠️ truncated descriptions done inline

---

### 6. **Leadership Grid**

**Where**

* Employees filtered by department
* Circular avatars
* Tooltip bios

**Canonical block**

```
leadership_grid
```

**Props**

* school
* department
* image_shape = circle
* max_items?

---

### 7. **Faculty & Staff Carousel**

**Where**

* Carousel in pairs
* Long bios
* Responsive behavior

**Canonical block**

```
staff_carousel
```

**Props**

* school
* department != leadership
* per_slide
* autoplay

---

### 8. **Primary CTA**

**Where**

```html
<a href="/registration-of-interest" class="btn btn-primary btn-lg">
```

**Canonical block**

```
primary_cta
```

---

## Page: `program`

Currently a **shell only**.

This is good news: it means we can design it *properly*.

Likely blocks (future):

* `program_hero`
* `program_overview`
* `program_curriculum`
* `program_outcomes`
* `program_cta`

---

# Part 2 — What this tells us (important conclusions)

### 1. You are already doing **block composition**

Just without guardrails.

### 2. Your biggest risk today is not “server scripts”

It’s:

* string-based content parsing
* inline Python in Web Pages
* implicit coupling between CSS/JS and templates

### 3. SEO is *mostly* good — but unowned

You need:

* one block to own `<h1>`
* predictable heading hierarchy
* block-level meta support

---

# Part 3 — Gaps revealed (what Proposal B must fix)

## ❌ Missing today

1. **Block registry**

   * Nothing names or constrains these patterns

2. **Block schema**

   * No validation of props
   * No editor-safe boundary

3. **Block renderer**

   * Rendering logic is duplicated across pages

4. **Data boundary**

   * Context scripts do too much (fetch + transform + format)

5. **SEO ownership**

   * Meta title/description/image are not block-owned

---

# Part 4 — Immediate next artifact to write

Before any refactor or Builder exploration, we now have enough to lock:

```
website_blocks_registry.md
```

### It will contain (v1):

| Block            | Status                       |
| ---------------- | ---------------------------- |
| hero_carousel    | LOCKED                       |
| tagline          | LOCKED                       |
| rich_cards_grid  | LOCKED (needs data refactor) |
| program_grid     | LOCKED                       |
| leadership_grid  | LOCKED                       |
| staff_carousel   | LOCKED                       |
| primary_cta      | LOCKED                       |
| program_* blocks | DEFERRED                     |

This registry becomes **law**.

---
