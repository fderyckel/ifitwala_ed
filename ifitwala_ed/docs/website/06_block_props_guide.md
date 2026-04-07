<!-- ifitwala_ed/docs/website/06_block_props_guide.md -->
# Block Props Guide (Complete)

**Audience:** Website editors, implementers
**Scope:** Builder‑lite v1 + Phase‑02 blocks
**Goal:** Exact props, types, rules, and examples for every block
**Canonical implementation source:** `ifitwala_ed/website/block_registry.py`
**Status (March 24, 2026):** Synced with implemented Builder-lite blocks including organization-media-backed image pickers for school-context forms and course catalog/detail blocks

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
* `Gallery Image.school_image` is the canonical file URL mirrored from the governed `Gallery Image.governed_file` reference when available.

### 0.5 Desk image picker behavior

On school-bound Desk forms (`School Website Page`, `Program Website Profile`, `Course Website Profile`, `Website Story`):

* image props in the builder use the governed `Organization Media` picker
* the picker can reuse visible organization/school media or upload a new governed image
* the saved JSON still stores the canonical file URL returned by the picker

### 0.6 Context-aware block availability

Block availability is enforced by parent DocType context (Desk picker + save-time validation).

| context | allowed block types |
| --- | --- |
| `School Website Page` + `page_type = Standard` | `hero`, `rich_text`, `section_carousel`, `program_list`, `course_catalog`, `leadership`, `cta`, `faq`, `content_snippet` |
| `School Website Page` + `page_type = Admissions` | all Standard blocks + `admissions_overview`, `admissions_steps`, `admission_cta` |
| `Program Website Profile` | all Standard blocks + `program_intro` |
| `Course Website Profile` | all Standard blocks + `course_intro`, `learning_highlights` |
| `Website Story` | Standard blocks only |

If a block type is outside the allowed set for the current context, save is blocked with a validation error.

### 0.7 Block script paths are system-owned

* Editors do not configure block JS paths in props.
* Optional enhancement scripts are defined in `Website Block Definition.script_path` via the canonical block registry.
* Current enhancement scripts:
  * `hero` -> `/assets/ifitwala_ed/website/blocks/hero.js`
  * `admission_cta` -> `/assets/ifitwala_ed/website/blocks/admission_cta.js`
  * `section_carousel` -> `/assets/ifitwala_ed/website/blocks/section_carousel.js`

### 0.8 Theme profile is separate from block props

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
| `background_image` | string | no | — | Single image for non‑carousel mode; selected via Organization Media picker in Desk |
| `images` | array | no | `[]` | Carousel images; if empty, fallback to `School.gallery_image` |
| `images[].image` | string | yes (per item) | — | Canonical file URL returned by Organization Media picker |
| `images[].alt` | string | no | — | Image alt text |
| `images[].caption` | string | no | — | Caption overlay |
| `autoplay` | boolean | no | `true` | Carousel auto‑advance |
| `interval` | integer | no | `5000` | Minimum `1000` ms |
| `variant` | string | no | `"default"` | Reserved for future layout variants |
| `image_fade_mode` | string | no | `"dark"` | `none`, `dark`, `primary`, or `accent` |
| `image_fade_opacity` | integer | no | `34` | 0..90 overlay opacity for readability |
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
  "image_fade_mode": "primary",
  "image_fade_opacity": 42,
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
  "content_html": "<p>Choosing a school is a major family decision. Our admissions experience is designed to feel personal, clear, and well paced from the very first step.</p><p>Families typically begin with an inquiry, continue with a conversation or campus visit when available, and then move into the application process with the support of the admissions team.</p>",
  "max_width": "wide"
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
    { "key": "inquire", "title": "Inquire", "description": "Share a few details so the admissions team can understand your child and answer your questions.", "icon": "mail" },
    { "key": "visit", "title": "Visit", "description": "If visits or conversations are available, we will help your family experience the campus, culture, and learning environment.", "icon": "map" },
    { "key": "apply", "title": "Apply", "description": "Complete the application when you are ready, including any forms, records, and supporting materials.", "icon": "file-text" }
  ],
  "layout": "horizontal"
}
```

---

## 4) Admission CTA

### Purpose

* Semantic admissions entry point (intent, not URL)
* `visit` remains valid, but starter admissions pages only seed that CTA when `School.admissions_visit_route` is configured
* Runtime fallback protects fresh public pages:
  * `visit` falls back to inquiry/apply routes when no visit route is configured
  * `apply` falls back to the admissions portal route when needed

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
  "label_override": "Get More Info",
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
| `hero_image` | string \| null | no | — | Canonical file URL returned by Organization Media picker |
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

* Entry point into school-offered, published Programs
* Published `Program Website Profile` rows render full linked detail cards
* Draft or missing `Program Website Profile` rows render teaser cards only (image/title, no detail link)

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

## 9) Section Carousel

### Purpose

* Long-scroll storytelling sections with text + compact image carousel
* Supports NIST-style repeated feature sections without changing page ownership rules

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | — | Section heading (`<h2>`) |
| `content_html` | string | no | — | Sanitized explanatory copy |
| `layout` | string | no | `"content_left"` | `content_left` or `content_right` |
| `items` | array | yes | — | Carousel image items (at least 1) |
| `items[].image` | string | yes (per item) | — | Canonical file URL returned by Organization Media picker |
| `items[].alt` | string | no | — | Alt text |
| `items[].caption` | string | no | — | Optional image caption |
| `autoplay` | boolean | no | `true` | Carousel auto‑advance |
| `interval` | integer | no | `5000` | Minimum `1000` ms |
| `cta_label` | string | no | — | Optional section CTA label |
| `cta_link` | string | no | — | Optional section CTA URL (validated) |

### Example
```json
{
  "heading": "Activities",
  "content_html": "<p>More than 300 activities across arts, service, and sports.</p>",
  "layout": "content_left",
  "items": [
    { "image": "/files/activity_01.jpg", "caption": "After-school sports", "alt": "Students at training" },
    { "image": "/files/activity_02.jpg", "caption": "Student clubs", "alt": "Students in club meeting" }
  ],
  "autoplay": true,
  "interval": 5200,
  "cta_label": "Learn More",
  "cta_link": "/schools/iss/activities"
}
```

---

## 10) Content Snippet

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

## 11) Leadership

### Purpose

* Displays school staff with `show_on_website = 1`
* Renders two premium carousels by default:
  * `Academic Leadership`
  * `Faculty & Staff`
* The leadership carousel resolves from `Designation.default_role_profile = "Academic Admin"` unless a manual `roles` designation filter is provided.
* Descendant-school inclusion is off by default; page authors must opt in per designation or role profile with `role_scopes`.

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `title` | string | no | — | Section title |
| `description` | string | no | — | Supporting intro copy |
| `leadership_title` | string | no | `Academic Leadership` | Primary carousel title |
| `staff_title` | string | no | `Faculty & Staff` | Secondary carousel title |
| `role_profiles` | array | no | `["Academic Admin"]` | Role profiles used to resolve the primary carousel from `Designation.default_role_profile` |
| `roles` | array | no | — | Manual designation override for the primary carousel |
| `role_scopes` | array | no | `[]` | Optional per-role school-scope overrides for the primary carousel. Each item targets either a `role` (Designation name) or `role_profile`, uses `school_scope = "current"` or `"current_and_descendants"`, and may set `descendant_depth` to stop at direct children or another explicit depth. |
| `limit` | integer | no | `4` | Max people to show in the primary carousel |
| `staff_limit` | integer | no | `8` | Max people to show in the staff carousel |
| `show_staff_carousel` | boolean | no | `true` | Hide/show the secondary staff carousel |

### Example
```json
{
  "title": "Teachers & Counselors",
  "description": "Meet the teachers and counselors shaping learning each day.",
  "leadership_title": "Academic Staff",
  "staff_title": "Faculty & Staff",
  "roles": ["Teacher", "Counselor"],
  "role_scopes": [
    {
      "role": "Teacher",
      "school_scope": "current_and_descendants",
      "descendant_depth": 1
    },
    {
      "role": "Counselor",
      "school_scope": "current"
    }
  ],
  "limit": 6,
  "staff_limit": 12,
  "show_staff_carousel": true
}
```

---

## 12) Staff Directory

Canonical provider: `ifitwala_ed.website.providers.staff_directory.get_context`

### Purpose

* Displays a school-scoped public staff directory from the canonical public-people service
* Exact-school only in the current implementation
* Intended for a dedicated `Faculty & Staff` or `Teachers & Counselors` website page
* Search and filter interactions run client-side on the rendered directory cards

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `title` | string | no | `Faculty & Staff` | Section title |
| `description` | string | no | — | Supporting intro copy |
| `designations` | array | no | `[]` | Optional exact `Designation.name` include list |
| `role_profiles` | array | no | `[]` | Optional exact `Designation.default_role_profile` include list |
| `show_search` | boolean | no | `true` | Show the search box |
| `show_designation_filter` | boolean | no | `true` | Show the role filter when multiple designations are present |
| `show_role_profile_filter` | boolean | no | `true` | Show the group filter when multiple role profiles are present |
| `limit` | integer or null | no | `null` | Optional cap for visible directory cards |
| `empty_state_title` | string | no | `No staff profiles available yet` | Empty-state heading when no staff match the server-side scope |
| `empty_state_text` | string | no | `This directory fills automatically when employees are marked to show on the website.` | Empty-state body copy |

### Filter semantics

* If `designations` and `role_profiles` are both blank, the directory includes all visible staff for the current school.
* If either list is populated, the directory includes employees matching any listed designation or any listed role profile.
* `designations` and `role_profiles` only affect which cards are rendered server-side. The interactive search/filter controls still operate client-side on that rendered subset.

### Example
```json
{
  "title": "Teachers & Counselors",
  "description": "Meet the people who shape learning, wellbeing, and school life each day.",
  "role_profiles": ["Academic Staff", "Counselor"],
  "show_search": true,
  "show_designation_filter": true,
  "show_role_profile_filter": true,
  "limit": null
}
```

---

## 13) CTA

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

---

## 13) Course Intro

### Purpose

* Course detail hero + intro
* Owns the page `<h1>` on course pages
* Renders overview, aims, and assessment summary from the `Course Website Profile` fields

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `heading` | string | yes | — | Rendered as `<h1>` |
| `content_html` | string | no | — | Optional override for `intro_text` |
| `hero_image` | string \| null | no | — | Optional override for profile hero image |
| `overview_heading` | string | no | `"Overview"` | Section label |
| `aims_heading` | string | no | `"What Students Will Develop"` | Section label |
| `assessment_heading` | string | no | `"Assessment Approach"` | Section label |
| `cta_intent` | string \| null | no | — | `inquire`, `visit`, `apply`, or `null` |

### Example
```json
{
  "heading": "Biology HL",
  "cta_intent": "inquire"
}
```

---

## 14) Learning Highlights

### Purpose

* Render curated, website-owned learning highlights for a course
* Preserve the public/private boundary by avoiding raw `Learning Unit` tree output

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `heading` | string | no | `"Learning Highlights"` | Section title |
| `limit` | integer \| null | no | all rows | Optional cap |

### Example
```json
{
  "heading": "Learning Highlights",
  "limit": 6
}
```

---

## 15) Course Catalog

### Purpose

* Display published public course pages as discoverable school-scoped cards

### Props (schema)

| prop | type | required | default | notes |
| --- | --- | --- | --- | --- |
| `show_intro` | boolean | no | `true` | Show course intro text |
| `show_course_group` | boolean | no | `true` | Show course group label |
| `show_related_programs` | boolean | no | `true` | Show related published program labels |
| `card_style` | string | no | `"standard"` | `standard` or `compact` |
| `limit` | integer \| null | no | `24` | Max courses to show |
| `empty_state_title` | string | no | `"Course catalog coming soon."` | Empty-state heading |
| `empty_state_text` | string | no | implementation default | Empty-state text |

### Example
```json
{
  "show_intro": true,
  "show_course_group": true,
  "show_related_programs": true,
  "card_style": "standard",
  "limit": 24
}
```
