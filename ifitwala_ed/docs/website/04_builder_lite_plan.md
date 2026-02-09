<!-- ifitwala_ed/docs/website/04_builder_lite_plan.md -->
# Builder-Lite v1 — Canonical Block Definitions & Implementation Plan
**Scope:** Home / School marketing pages
**Blocks:** Hero, Rich Text, Program List, Leadership, CTA
**Non-goal:** visual editor UI (comes later)
**Hard constraint:** **no server scripts**, no DB-stored code

---

## 0. SEO & templating principles (lock these first)

These pages are **marketing pages**, not apps. SEO must be first-class.

### 0.1 Page-level SEO (mandatory)

Each rendered page must output:

* `<title>` — unique, school-specific
* `<meta name="description">`
* `<link rel="canonical">`
* Structured headings (`h1` once, logical `h2/h3`)
* Crawlable HTML (no JS-only content)
* Static URLs (no querystring routing)

**Implication:**
All blocks must render **real HTML at request time**, not fetch content via JS.

---

### 0.2 Heading rules (non-negotiable)

* Exactly **one `<h1>` per page**
* Hero block **owns the H1**
* All other blocks start at `h2` or lower
* Never let editors choose heading level freely

This prevents SEO dilution.

---

### 0.3 Template strategy (important)

We use **block-specific Jinja templates**, not inline HTML blobs.

```
ifitwala_ed/
  website/
    blocks/
      hero.html
      rich_text.html
      program_list.html
      leadership.html
      cta.html
```

Each template:

* is semantic HTML
* has no logic beyond loops / conditionals
* receives **already-prepared data**

---

## 1. Core architecture (recap, now actionable)

### 1.1 Page record

`School Website Page`

* route
* school
* title
* meta_description
* blocks (ordered)

No HTML. No Python.

---

### 1.2 Block registry (system-owned)

`Website Block Definition`

Fields:

* `block_type`
* `template_path`
* `provider_path`
* `props_schema` (JSON Schema)
* `seo_role` (e.g. `owns_h1`, `content`, `supporting`)
* `is_core` (locked)

This registry is what makes Builder-lite safe.

---

### 1.3 Providers (trusted code)

Location:

```
ifitwala_ed/website/providers/
```

Pattern:

```python
def get_context(*, school, page, block_props):
    return {
        "data": ...,
        "seo": ...,
    }
```

Providers:

* fetch data
* shape it for templates
* enforce limits (count, visibility)
* handle image fallback
* cache where safe

Templates **never query the DB**.

---

## 2. Canonical Block Definitions (v1)

Below are **exact block specs** you can implement.

---

## Block 1 — HERO (SEO anchor)

### Purpose

* Page identity
* Primary message
* SEO anchor

### SEO role

* **Owns `<h1>`**
* Can emit structured data (later)

### Props schema

```json
{
  "title": "string (required)",
  "subtitle": "string",
  "background_image": "Image",
  "variant": "default | split | centered",
  "cta_label": "string",
  "cta_link": "string"
}
```

### Provider responsibilities

* Resolve image URLs (use your existing fallback logic)
* Validate CTA link is internal or whitelisted
* Nothing dynamic beyond that

### Template rules

* Outputs `<section>`
* Contains:

  * `<h1>{{ title }}</h1>`
  * `<p>` subtitle (optional)
* No JS dependency

---

## Block 2 — RICH TEXT (content body)

### Purpose

* Editorial content
* SEO depth
* Keyword relevance

### SEO role

* Main body content (`h2`, `h3`, lists, links)

### Props schema

```json
{
  "content_html": "HTML (sanitized)",
  "max_width": "narrow | normal | wide"
}
```

### Provider responsibilities

* Sanitize HTML (strip scripts, iframes)
* Optionally auto-inject internal links later

### Template rules

* Wrap content in `<section>`
* Ensure headings inside start at `<h2>`
* No inline styles

---

## Block 3 — PROGRAM LIST (dynamic but crawlable)

### Purpose

* Show offerings
* Internal linking (SEO gold)

### SEO role

* Supporting content
* Emits multiple internal links

### Props schema

```json
{
  "school_scope": "current | all",
  "show_intro": "boolean",
  "card_style": "standard | compact",
  "limit": "integer (default 6)"
}
```

### Provider responsibilities

* Fetch published Programs for school
* Apply limit
* Pre-truncate descriptions
* Build canonical program URLs

### Template rules

* `<section>`
* Optional `<h2>`
* `<ul>` or `<div>` grid with `<a href="/program/...">`
* Titles must be `<h3>`

**Important:**
Do not lazy-load program data via JS. Render server-side.

---

## Block 4 — LEADERSHIP

### Purpose

* Trust
* Authority
* Human signal (SEO quality)

### SEO role

* Supporting content
* Name/entity signals

### Props schema

```json
{
  "title": "string",
  "roles": ["Head", "Principal", "Director"],
  "limit": "integer"
}
```

### Provider responsibilities

* Fetch Employees with `show_on_website = 1`
* Resolve images (small_)
* Sort by role priority

### Template rules

* `<section>`
* `<h2>`
* Each leader:

  * `<h3>` name
  * `<p>` role
  * `<img alt="Full Name – Role">`

Alt text matters for SEO.

---

## Block 5 — CTA (conversion, but semantic)

### Purpose

* Admissions / Contact
* Funnel entry

### SEO role

* Supporting
* No heading abuse

### Props schema

```json
{
  "title": "string",
  "text": "string",
  "button_label": "string",
  "button_link": "string"
}
```

### Provider responsibilities

* Validate link
* No data fetch

### Template rules

* `<section>`
* `<h2>` (optional, if not repetitive)
* `<a>` styled as button (still semantic)

---

## 3. Rendering flow (step-by-step)

1. HTTP request → route resolver
2. Resolve `School Website Page`
3. For each block:

   * load block definition
   * validate props against schema
   * call provider
4. Assemble context:

   ```python
   {
     "page": page,
     "blocks": rendered_blocks
   }
   ```
5. Render master page template:

   * inject `<title>`, meta
   * loop blocks in order

---

## 4. Asset strategy (SEO-safe)

* CSS:

  * `website.css` (Tailwind entrypoint)
  * `website.bundle.css` (build output referenced by templates)
* JS:

  * `website.js` (built to `website.bundle.js`)
  * `website.bundle.js` (build output referenced by templates)
  * `image_fallback.js` (raw helper)
  * enhancement only (no data fetch)

Build notes:

* Tailwind config: `tailwind.website.config.js`
* Run `yarn build` (or `bench build`) after CSS/template changes.
* Content edits in Desk do **not** require a rebuild.
* Tailwind is scoped to `#ifitwala-page-root` with preflight disabled (no global resets).
* Bootstrap is not used on public website pages.
* Website catch-all routing must preserve framework namespaces (`/app`, `/desk`, `/api`, `/assets`, `/files`) and core website assets (`/website_script.js`, `/website_style.css`) so Desk, APIs, login, and public templates all resolve correctly.
* Guest users get an explicit `Login` CTA in the custom website header (`/login`).
* `Website Settings` top bar is intentionally minimal (`Home`, `Login`) to avoid conflicting menu trees on framework-managed login pages; public website navigation is generated from published `School Website Page.full_route` values.

Critical content **must not depend on JS**.

---

## 5. Implementation plan (coding instructions)

### Phase 1 — Foundation

1. Create DocTypes:

   * `School Website Page`
   * `Website Block Definition`
2. Seed block definitions for the 5 blocks
3. Create block template files
4. Add default new-site page scaffold:
   * school web identity (`website_slug`, publication)
   * `School Website Page` records for `/`, `about`, `admissions`
   * navigation built from published page `full_route` values

### Phase 2 — Providers

5. Implement providers (one file per block)
6. Add Redis caching where safe (Program list, Leadership)

### Phase 3 — Renderer

7. Implement page renderer (controller or hook)
8. Replace existing `/home` route to use new system

### Phase 4 — Migration

9. Map existing Web Page content → blocks
10. Disable `server_script_enabled`
11. Delete old context scripts

---

## 6. Strategic outcome (why this works)

* SEO-grade HTML
* Live updates without rebuilds
* No arbitrary code execution
* Same mental model as SPA components
* Scales to:

  * blog blocks
  * testimonial blocks
  * admissions funnels
  * per-school overrides

---



Approved. Moving to **execution artifacts**.

Below are **authoritative coding instructions + concrete schemas** to implement **Builder-lite v1** up to the 5 canonical blocks, with SEO-first templating. This is written so you (or another agent) can implement without reinterpretation.

---

# Builder-Lite v1 — Execution Pack (Authoritative)

## Scope lock

* Public marketing pages only (School/Home)
* Native Frappe rendering (no SPA here)
* **No `server_script`**, no DB-stored code
* Live data, crawlable HTML, SEO-first

---

## 1. DocTypes (exact schemas)

### 1.1 `School Website Page`

**Purpose:** Page instance (route + blocks)

**Key properties**

* Single source of truth for page composition
* One page per `(school, route)`

**Fields**

| Field              | Type          | Notes                              |
| ------------------ | ------------- | ---------------------------------- |
| `school`           | Link (School) | required                           |
| `route`            | Data          | `/` (root) or `admissions`         |
| `full_route`       | Data          | read-only canonical route          |
| `title`            | Data          | `<title>`                          |
| `meta_description` | Small Text    | `<meta>`                           |
| `is_published`     | Check         |                                    |
| `blocks`           | Table         | child: `School Website Page Block` |

**Indexes**

* `(school, full_route)` unique

---

### 1.2 `School Website Page Block` (child)

**Purpose:** Ordered block instances

**Fields**

| Field        | Type   | Notes               |
| ------------ | ------ | ------------------- |
| `block_type` | Select | must match registry |
| `order`      | Int    | render order        |
| `props`      | Text   | JSON only           |
| `is_enabled` | Check  |                     |

No HTML. No code.

---

### 1.3 `Website Block Definition` (system-owned)

**Purpose:** Block registry + governance

**Fields**

| Field           | Type        | Notes                              |
| --------------- | ----------- | ---------------------------------- |
| `block_type`    | Data        | e.g. `hero`                        |
| `label`         | Data        | UI label                           |
| `template_path` | Data        | Jinja path                         |
| `provider_path` | Data        | Python dotted path                 |
| `props_schema`  | Code (JSON) | JSON Schema                        |
| `seo_role`      | Select      | `owns_h1`, `content`, `supporting` |
| `is_core`       | Check       | locked                             |

Seed data only. Users cannot create/edit.

---

## 2. File layout (locked)

```text
ifitwala_ed/
  website/
    renderer.py
    providers/
      hero.py
      rich_text.py
      program_list.py
      leadership.py
      cta.py
    blocks/
      hero.html
      rich_text.html
      program_list.html
      leadership.html
      cta.html
    templates/
      page.html   # master layout
```

---

## 3. Renderer (core engine)

### `website/renderer.py`

Responsibilities:

* Resolve page by `(school, route)`
* Validate publication
* Load block definitions
* Validate props against schema
* Call providers
* Enforce SEO rules
* Render final HTML

**SEO enforcement (mandatory)**

* Exactly **one** block with `seo_role = owns_h1`
* Hero must be first enabled block
* Raise error if violated (fail fast)

**Pseudo-flow**

```python
page = get_page(school, route)
blocks = []

for block in page.blocks:
	if not block.is_enabled:
		continue

	defn = get_block_definition(block.block_type)
	props = validate_props(block.props, defn.schema)
	ctx = call_provider(defn.provider_path, school, page, props)

	blocks.append({
		"template": defn.template_path,
		"props": props,
		"data": ctx["data"],
	})

render("page.html", {
	"page": page,
	"blocks": blocks,
})
```

---

## 4. Providers (A+ compliant)

### Provider contract (locked)

```python
def get_context(*, school, page, block_props) -> dict:
	return {
		"data": {...}
	}
```

Rules:

* No rendering
* No HTML
* No request context
* Cache allowed (Redis)

---

## 5. Canonical blocks — exact implementation guidance

### 5.1 HERO

* **SEO role:** `owns_h1`
* Provider: trivial
* Template:

  * `<section>`
  * `<h1>{{ props.title }}</h1>`
  * subtitle `<p>`
  * `<a>` CTA
* Image handled via existing fallback utility

---

### 5.2 RICH TEXT

* **SEO role:** `content`
* Provider:

  * sanitize HTML
* Template:

  * `<section>`
  * render HTML
  * enforce `h2+` only (no h1 allowed)

---

### 5.3 PROGRAM LIST

* **SEO role:** `supporting`
* Provider:

  * fetch published programs for school
  * limit
  * pre-build URLs
* Template:

  * `<section>`
  * `<h2>`
  * program cards with `<h3>` titles
  * `<a href>` links (crawlable)

---

### 5.4 LEADERSHIP

* **SEO role:** `supporting`
* Provider:

  * employees with `show_on_website = 1`
  * role filtering
* Template:

  * `<section>`
  * `<h2>`
  * `<h3>` names
  * `<img alt="Name – Role">`

---

### 5.5 CTA

* **SEO role:** `supporting`
* Provider: none (pass-through)
* Template:

  * `<section>`
  * optional `<h2>`
  * semantic `<a>`

---

## 6. Master template (`page.html`)

Responsibilities:

* `<title>` from page
* `<meta description>`
* `<link rel="canonical">`
* Load CSS (`website.bundle.css`)
* Loop blocks in order
* **No JS data fetch**

---

## 7. Migration instructions (from current Web Pages)

1. Identify current `/home` Web Page
2. Map:

   * hero → HERO
   * intro text → RICH TEXT
   * programs loop → PROGRAM LIST
   * staff → LEADERSHIP
   * admissions link → CTA
3. Create `School Website Page` record
4. Populate blocks
5. Verify render
6. Disable `server_script_enabled`
7. Delete all legacy `Web Page` records (patch: `remove_legacy_web_pages`)
8. Remove legacy Web Page fixtures (`setup/data/web_page.json`)

---

## 8. Non-goals (explicit)

* No visual editor yet
* No Builder dependency
* No tenant scripting
* No JS-rendered content

---

# 1. Provider file skeletons (authoritative)

Location (locked):

```
ifitwala_ed/website/providers/
```

All providers **must** follow the same contract. No exceptions.

---

## 1.1 Common provider contract (mental model)

```python
def get_context(*, school, page, block_props) -> dict:
	"""
	Return data only.
	No HTML.
	No rendering.
	No request access.
	"""
	return {
		"data": {...}
	}
```

* `school`: School Doc (already resolved)
* `page`: School Website Page Doc
* `block_props`: validated dict (already schema-checked)
* Return value **must** be JSON-serializable

---

## 1.2 `hero.py`

```python
# ifitwala_ed/website/providers/hero.py

def get_context(*, school, page, block_props):
	"""
	HERO block
	SEO owner: <h1>
	Pure pass-through, image resolution handled elsewhere.
	"""
	return {
		"data": {
			"title": block_props.get("title"),
			"subtitle": block_props.get("subtitle"),
			"background_image": block_props.get("background_image"),
			"cta_label": block_props.get("cta_label"),
			"cta_link": block_props.get("cta_link"),
			"variant": block_props.get("variant", "default"),
		}
	}
```

No DB access. No cache.

---

## 1.3 `rich_text.py`

```python
# ifitwala_ed/website/providers/rich_text.py

from ifitwala_ed.utilities.html_sanitizer import sanitize_html

def get_context(*, school, page, block_props):
	"""
	Rich text editorial content.
	Sanitize aggressively.
	"""
	content = block_props.get("content_html") or ""

	return {
		"data": {
			"content": sanitize_html(
				content,
				allow_headings_from="h2"  # enforce SEO rule
			),
			"max_width": block_props.get("max_width", "normal"),
		}
	}
```

> Note: `sanitize_html` should already exist or be created once centrally.
> No per-block sanitizers.

---

## 1.4 `program_list.py`

```python
# ifitwala_ed/website/providers/program_list.py

from frappe.utils import cint
from ifitwala_ed.website.cache import redis_cache

@redis_cache(ttl=3600)
def _get_program_profiles(school_scope, school, limit):
	# implement later
	return []

def get_context(*, school, page, block_props):
	"""
	Program list – dynamic but crawlable.
	"""
	limit = cint(block_props.get("limit") or 6)
	school_scope = block_props.get("school_scope") or "current"
	programs = _get_program_profiles(school_scope=school_scope, school=school.name, limit=limit)
	return {
		"data": {
			"programs": programs,
			"show_intro": bool(block_props.get("show_intro")),
			"card_style": block_props.get("card_style") or "standard",
		}
	}
```

Notes:

* Cache **only** the DB fetch
* Provider returns already-shaped data (title, url, excerpt)

---

## 1.5 `leadership.py`

```python
# ifitwala_ed/website/providers/leadership.py

from frappe.utils import cint
from ifitwala_ed.website.cache import redis_cache

@redis_cache(ttl=3600)
def _get_leaders(school, roles, limit):
	# implement later
	return []

def get_context(*, school, page, block_props):
	"""
	Leadership / authority block.
	"""
	limit = cint(block_props.get("limit") or 4)
	roles = block_props.get("roles") or []

	leaders = _get_leaders(
		school=school.name,
		roles=roles,
		limit=limit,
	)

	return {
		"data": {
			"title": block_props.get("title"),
			"leaders": leaders,
		}
	}
```

Alt text, image URLs, and role labels are resolved **here**, not in the template.

---

## 1.6 `cta.py`

```python
# ifitwala_ed/website/providers/cta.py

def get_context(*, school, page, block_props):
	"""
	Call-to-action block.
	No data fetching.
	"""
	return {
		"data": {
			"title": block_props.get("title"),
			"text": block_props.get("text"),
			"button_label": block_props.get("button_label"),
			"button_link": block_props.get("button_link"),
		}
	}
```

---

# 2. Master page template (SEO-first)

Location (locked):

```
ifitwala_ed/website/templates/page.html
```

This is the **only** page-level template.

---

## `page.html` (authoritative)

```jinja
{# ifitwala_ed/website/templates/page.html #}
<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="utf-8">

	<title>{{ page.title }}</title>

	{% if page.meta_description %}
	<meta name="description" content="{{ page.meta_description }}">
	{% endif %}

	<link rel="canonical" href="{{ frappe.utils.get_url(page.route) }}">

	<meta name="viewport" content="width=device-width, initial-scale=1">

	{# Core CSS #}
	<link rel="stylesheet" href="/assets/ifitwala_ed/css/website.bundle.css">
</head>

<body>
	<main id="ifitwala-page-root">

		{% for block in blocks %}
			{% include block.template with context %}
		{% endfor %}

	</main>

	{# Enhancement JS only – no data fetch #}
	<script src="/assets/ifitwala_ed/website/image_fallback.js" defer></script>
	<script src="/assets/ifitwala_ed/js/website.bundle.js" defer></script>
</body>
</html>
```

### Why this is SEO-correct

* Full HTML rendered server-side
* All content crawlable without JS
* Canonical URL explicit
* One `<main>` landmark
* No inline scripts
* No dynamic DOM mutation required for content

---

# 3. Block templates (guidance, not full code)

Each block template:

* Receives `props` and `data`
* Emits semantic HTML
* **Never** queries DB
* **Never** chooses heading level arbitrarily

Example pattern:

```jinja
<section class="block block-program-list">
	{% if data.title %}
		<h2>{{ data.title }}</h2>
	{% endif %}
	...
</section>
```

Hero template is the **only** one allowed to emit `<h1>`.

---
