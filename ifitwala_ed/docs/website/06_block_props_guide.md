# Block Props Guide (Builder-lite v1)

**Audience:** Website managers and implementers
**Scope:** Public marketing pages (Builder-lite v1)

---

## 1. What are props?

**Props** are the per-block settings stored as JSON on each block row. They control:

* text content (titles, labels)
* links
* layout options (where allowed)
* visibility of optional fields

Props are validated against a JSON schema for each block type.

---

## 2. How to enter props

* Props must be **valid JSON**.
* Example JSON:

```
{"title": "Ifitwala Secondary School"}
```

Common mistakes:

* Missing quotes around keys or strings
* Trailing commas
* Using single quotes instead of double quotes

---

## 3. Supported blocks and their props

### 3.1 `hero`

**Purpose:** Page hero + SEO H1, optional carousel

**Props**

| Key | Type | Required | Notes |
| --- | --- | --- | --- |
| `title` | string | yes | Rendered as `<h1>` |
| `subtitle` | string | no | Optional subtitle text |
| `background_image` | string | no | File URL or attachment URL |
| `images` | array | no | Carousel images (auto-fallback to `School.gallery_image` when empty) |
| `autoplay` | boolean | no | Default true |
| `interval` | integer | no | Default 5000 (min 1000) |
| `variant` | string | no | One of: `default`, `split`, `centered` |
| `cta_label` | string | no | CTA button label |
| `cta_link` | string | no | Must be `/path` or `https://...` |

**Example (single image)**

```
{"title": "Ifitwala Secondary School", "subtitle": "A community of learners"}
```

**Example (carousel)**

```
{
  "title": "Ifitwala Secondary School",
  "images": [
    {"image": "/files/hero_1.jpg", "alt": "Campus entrance"},
    {"image": "/files/hero_2.jpg", "caption": "Student life"}
  ],
  "autoplay": true,
  "interval": 5000
}
```

---

### 3.2 `rich_text`

**Purpose:** Editorial content section

**Props**

| Key | Type | Required | Notes |
| --- | --- | --- | --- |
| `content` | string | yes | Sanitized HTML, headings start at `h2` |
| `max_width` | string | no | One of: `narrow`, `normal`, `wide` |

**Example**

```
{"content": "<h2>About Us</h2><p>...</p>", "max_width": "normal"}
```

---

### 3.3 `program_list`

**Purpose:** List programs for a school (from Program Offering)

**Props**

| Key | Type | Required | Notes |
| --- | --- | --- | --- |
| `title` | string | no | Section heading |
| `program_category` | string | no | Matches `Program.parent_program` |
| `limit` | integer | no | Default 6 |
| `show_description` | boolean | no | Show excerpt |

**Example**

```
{"title": "Academic Programs", "limit": 6, "show_description": true}
```

---

### 3.4 `leadership`

**Purpose:** Leadership grid

**Props**

| Key | Type | Required | Notes |
| --- | --- | --- | --- |
| `title` | string | no | Section heading |
| `roles` | array[string] | no | Filters `Employee.designation` |
| `limit` | integer | no | Default 4 |

**Example**

```
{"title": "Leadership Team", "roles": ["Principal", "Director"], "limit": 4}
```

---

### 3.5 `cta`

**Purpose:** Primary call-to-action

**Props**

| Key | Type | Required | Notes |
| --- | --- | --- | --- |
| `title` | string | no | Optional heading |
| `text` | string | no | Supporting text |
| `button_label` | string | yes | CTA label |
| `button_link` | string | yes | Must be `/path` or `https://...` |

**Example**

```
{"title": "Book a Visit", "text": "Schedule a tour.", "button_label": "Contact Us", "button_link": "/contact"}
```

---

## 4. Validation rules (important)

* `hero` must be the **first enabled block** on the page
* Exactly **one** block must own the H1 (the `hero` block)
* CTA links must be internal `/...` or `https://...`
* Props must be valid JSON

---

## 5. Troubleshooting

**Error: jsonschema is required**

Install `jsonschema` in the bench environment:

```
./env/bin/pip install jsonschema
```

**Error: Page has no enabled blocks**

Make sure at least one block is enabled and `hero` is first.

---

{
  "title": "Ifitwala Secondary School",
  "subtitle": "Home of the Brave",
  "images": [
    { "image": "/files/hero_01.jpg", "caption": "Campus sunrise", "alt": "Campus at dawn" },
    { "image": "/files/hero_02.jpg", "caption": "Student life", "alt": "Students on campus" }
  ],
  "autoplay": true,
  "interval": 6000,
  "cta_label": "Apply Now",
  "cta_link": "/admissions"
}
