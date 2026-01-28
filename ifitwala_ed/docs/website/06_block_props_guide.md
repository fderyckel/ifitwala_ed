<!-- ifitwala_ed/docs/website/06_block_props_guide.md -->
# Block Props Guide (Complete)

**Audience:** Website editors, implementers
**Scope:** Builder‑lite v1 blocks (Hero, Rich Text, Program List, Leadership, CTA)
**Goal:** Exact props, types, rules, and examples for every block

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
  "cta_link": "/admissions"
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

## 2) Rich Text

### Purpose

* General content (history, mission, admissions steps)
* HTML is rendered as‑is (editor must provide clean markup)

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `content` | string | yes | — | HTML content (safe‑rendered) |
| `max_width` | string | no | `"normal"` | `narrow`, `normal`, or `wide` |

### Example
```json
{
  "content": "<h2>Our History</h2><p>Founded in 1998, we serve learners from diverse backgrounds.</p>",
  "max_width": "wide"
}
```

---

## 3) Program List

### Purpose

* List programs **offered by this school**
* Source of truth: Program Offering

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `title` | string | no | — | Optional section title |
| `program_category` | string | no | — | Filter by category if provided |
| `limit` | integer | no | — | Max programs to show |
| `show_description` | boolean | no | `false` | Show program description |

### Example
```json
{
  "title": "Programs",
  "program_category": null,
  "limit": 6,
  "show_description": true
}
```

---

## 4) Leadership

### Purpose

* Displays staff with `show_on_website = 1`
* Optional department filter

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `title` | string | no | — | Section title |
| `department` | string | no | — | Filter by department |
| `limit` | integer | no | — | Max staff to show |

### Example
```json
{
  "title": "Leadership & Administration",
  "department": "Administration",
  "limit": 9
}
```

---

## 5) CTA

### Purpose

* A focused call‑to‑action block

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `title` | string | no | — | Heading |
| `text` | string | no | — | Supporting text |
| `button_label` | string | no | — | Button label |
| `button_link` | string | no | — | CTA URL (validated) |

### Example
```json
{
  "title": "Ready to apply?",
  "text": "Start your admissions journey today.",
  "button_label": "Apply Now",
  "button_link": "https://apply.school.edu"
}
```

---

## 6) Troubleshooting

**Validation error: Missing block definitions**

* Run the block definition seed/patch for existing sites.

**Validation error: jsonschema missing**

* Install `jsonschema` in the bench env and run `bench build` if needed.

**Page has no enabled blocks**

* Ensure at least one block row is enabled on the School Website Page.

---

## 7) Field‑level glossary

* **props**: JSON configuration for a block (stored on `School Website Page Block`).
* **block definition**: System record describing block schema and provider.
* **provider**: Python function that loads/derives data for the block.
