<!-- ifitwala_ed/docs/website/06_block_props_guide.md -->
# Block Props Guide (Complete)

**Audience:** Website editors, implementers  
**Scope:** Builder‑lite v1 + Phase‑02 blocks  
**Goal:** Exact props, types, rules, and examples for every block
**Canonical implementation source:** `ifitwala_ed/website/block_registry.py`
**Status (February 12, 2026):** Synced with implemented A1/A2/B1/B2/C1/C2/D1/D2 baseline

---

## 0) Universal rules

### 0.1 Props are JSON

* Props must be **valid JSON** (double quotes, no trailing commas).
* Properties not defined in the schema are rejected.

### 0.2 Content vs build

* Editing **props** does **not** require a build.
* Editing **templates / CSS / JS** requires `yarn build` (or `bench build`).

### 0.3 CTA link validation

Allowed values:

* `/path` (internal)
* `https://example.com` (external)

Disallowed:

* `javascript:`
* `data:`
* `mailto:`
* protocol‑relative `//example.com`

### 0.4 Image fallback

* `hero.images` is optional.
* If `hero.images` is **empty or missing**, the hero carousel uses `School.gallery_image` rows (field `school_image`).

### 0.5 Context-aware block availability

Block availability is enforced by parent DocType context (Desk picker + save-time validation).

| context | allowed block types |
| --- | --- |
| `School Website Page` + `page_type = Standard` | `hero`, `rich_text`, `program_list`, `leadership`, `cta`, `faq`, `content_snippet` |
| `School Website Page` + `page_type = Admissions` | all Standard blocks + `admissions_overview`, `admissions_steps`, `admission_cta` |
| `Program Website Profile` | all Standard blocks + `program_intro` |
| `Website Story` | Standard blocks only |

If a block type is outside the allowed set for the current context, save is blocked with a validation error.

### 0.6 Block script paths are system-owned

* Editors do not configure block JS paths in props.
* Optional enhancement scripts are defined in `Website Block Definition.script_path` via the canonical block registry.
* Current enhancement scripts:
  * `hero` -> `/assets/ifitwala_ed/website/blocks/hero.js`
  * `admission_cta` -> `/assets/ifitwala_ed/website/blocks/admission_cta.js`

### 0.7 Theme profile is separate from block props

* Brand tokens (colors, type scale, spacing density, hero style, motion toggle) come from `Website Theme Profile`.
* Theme tokens are resolved by scope (`School -> Organization -> Global`) in renderer code.
* Block props remain content/config contracts only.

---

## 1) Hero

### Purpose

* Owns the page `<h1>` and top banner
* Can be a single image or carousel

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `title` | string | yes | — | Rendered as `<h1>` |
| `subtitle` | string | no | — | Optional secondary text |
| `background_image` | string | no | — | Single image for non‑carousel mode |
| `images` | array | no | `[]` | Carousel images; if empty, fallback to `School.gallery_image` |
| `images[].image` | string | yes (per item) | — | File URL |
| `images[].alt` | string | no | — | Image alt text |
| `images[].caption` | string | no | — | Caption overlay |
| `autoplay` | boolean | no | `true` | Carousel auto‑advance |
| `interval` | integer | no | `5000` | Minimum `1000` ms |
| `variant` | string | no | `"default"` | Reserved for future layout variants |
| `cta_label` | string | no | — | Button label |
| `cta_link` | string | no | — | CTA URL (validated) |

**Validation note**

`hero` props are strictly validated. Only the fields listed above are allowed.  
Legacy shapes like `primary_cta` are rejected and will throw a render error.

### Example: carousel with images
```json
{
  "title": "Ifitwala Secondary School",
  "subtitle": "Home of the Brave",
  "images": [
    { "image": "/files/hero_01.jpg", "caption": "Campus sunrise", "alt": "Campus at dawn" },
    { "image": "/files/hero_02.jpg", "caption": "Student life", "alt": "Students on campus" }
  ],
  "autoplay": true,
  "interval": 6000,
  "cta_label": "Book a Visit",
  "cta_link": "/apply/inquiry"
}
```

### Example: single image
```json
{
  "title": "Admissions",
  "subtitle": "A clear, supportive process",
  "background_image": "/files/hero_admissions.jpg",
  "cta_label": "Apply Now",
  "cta_link": "https://apply.school.edu"
}
```

---

## 2) Admissions Overview

### Purpose

* Admissions narrative anchor
* Owns the page `<h1>` on admissions pages

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | — | Rendered as `<h1>` |
| `content_html` | string | yes | — | Sanitized HTML |
| `max_width` | string | no | `"normal"` | `narrow`, `normal`, or `wide` |

### Example
```json
{
  "heading": "Admissions",
  "content_html": "<p>We welcome families who value curiosity, care, and growth.</p>",
  "max_width": "normal"
}
```

---

## 3) Admissions Steps

### Purpose

* Visualize the admissions journey without exposing workflow logic

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `steps` | array | yes | — | Must include at least 2 steps |
| `steps[].key` | string | yes | — | `inquire`, `visit`, `apply` |
| `steps[].title` | string | yes | — | Displayed heading |
| `steps[].description` | string | no | — | Plain text |
| `steps[].icon` | string \| null | no | — | `mail`, `map`, `file-text`, or `null` |
| `layout` | string | no | `"horizontal"` | `horizontal` or `vertical` |

### Example
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

---

## 4) Admission CTA

### Purpose

* Semantic admissions entry point (intent, not URL)

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `intent` | string | yes | — | `inquire`, `visit`, `apply` |
| `label_override` | string \| null | no | — | Optional custom label |
| `style` | string | no | `"primary"` | `primary`, `secondary`, `outline` |
| `icon` | string \| null | no | — | `mail`, `map`, `file-text`, or `null` |
| `tracking_id` | string \| null | no | — | Optional analytics ID |

### Example
```json
{
  "intent": "inquire",
  "label_override": null,
  "style": "primary",
  "icon": "mail"
}
```

---

## 5) FAQ

### Purpose

* Parent friction removal + SEO

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `items` | array | yes | — | At least 1 item |
| `items[].question` | string | yes | — | Question text |
| `items[].answer_html` | string | yes | — | Sanitized HTML |
| `enable_schema` | boolean | no | `true` | Injects JSON‑LD if true |
| `collapsed_by_default` | boolean | no | `true` | Uses `<details>` |

### Example
```json
{
  "items": [
    { "question": "What curriculum do you offer?", "answer_html": "<p>We offer the IB continuum...</p>" }
  ],
  "enable_schema": true,
  "collapsed_by_default": true
}
```

---

## 6) Program Intro

### Purpose

* Program detail hero + intro
* Owns the page `<h1>` on program pages

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | — | Rendered as `<h1>` |
| `content_html` | string | no | — | Sanitized HTML |
| `hero_image` | string \| null | no | — | File URL |
| `cta_intent` | string \| null | no | — | `inquire`, `visit`, `apply`, or `null` |

### Example
```json
{
  "heading": "IB Diploma Programme",
  "content_html": "<p>The IB DP prepares students...</p>",
  "hero_image": "/files/ib_dp_hero.jpg",
  "cta_intent": "apply"
}
```

---

## 7) Program List

### Purpose

* Entry point into Program pages
* Displays only published Program Website Profiles

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `school_scope` | string | no | `"current"` | `current` or `all` |
| `show_intro` | boolean | no | `false` | Show program intro |
| `card_style` | string | no | `"standard"` | `standard` or `compact` |
| `limit` | integer \| null | no | `6` | Max programs to show |

### Example
```json
{
  "school_scope": "current",
  "show_intro": true,
  "card_style": "standard",
  "limit": 6
}
```

---

## 8) Rich Text

### Purpose

* General content (history, mission, admissions steps)
* HTML is rendered as‑is (sanitized)

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `content_html` | string | yes | — | HTML content (safe‑rendered) |
| `max_width` | string | no | `"normal"` | `narrow`, `normal`, or `wide` |

### Example
```json
{
  "content_html": "<h2>Our History</h2><p>Founded in 1998, we serve learners from diverse backgrounds.</p>",
  "max_width": "wide"
}
```

---

## 9) Content Snippet

### Purpose

* Reusable editorial fragments

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `snippet_id` | string | yes | — | Must exist |
| `allow_override` | boolean | no | `false` | Reserved for future use |

Snippet resolution order is deterministic:

1. School-scoped snippet (`scope_type = School`, same school)
2. Organization-scoped snippet (`scope_type = Organization`, same organization)
3. Global snippet (`scope_type = Global`)

`snippet_id` is unique per scope target (not globally unique across all schools/organizations).

### Example
```json
{
  "snippet_id": "ADMISSIONS-BLURB",
  "allow_override": false
}
```

---

## 10) Leadership

### Purpose

* Displays staff with `show_on_website = 1`
* Optional role filter

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `title` | string | no | — | Section title |
| `roles` | array | no | — | Role filter (designation) |
| `limit` | integer | no | — | Max staff to show |

### Example
```json
{
  "title": "Leadership & Administration",
  "roles": ["Head", "Principal"],
  "limit": 9
}
```

---

## 11) CTA

### Purpose

* A focused call‑to‑action block

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `title` | string | no | — | Heading |
| `text` | string | no | — | Supporting text |
| `button_label` | string | yes | — | Button label |
| `button_link` | string | yes | — | CTA URL (validated) |

### Example
```json
{
  "title": "Ready to apply?",
  "text": "Start your admissions journey today.",
  "button_label": "Apply Now",
  "button_link": "https://apply.school.edu"
}
```
