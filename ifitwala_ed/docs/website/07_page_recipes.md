<!-- ifitwala_ed/docs/website/07_page_recipes.md -->
# Page Recipes (Home / About / Admissions)

**Audience:** Marketing, admissions, and website managers
**Goal:** Fast, consistent page setup using the 5 canonical blocks
**Blocks:** hero, rich_text, program_list, leadership, cta

---

## 1) Home Page (School Root)

**Route input:** `/` (root page only; system stores `/<school-slug>` in `full_route`)

**Suggested block order**

1. **hero**
2. **rich_text** (intro)
3. **program_list** (featured programs)
4. **leadership** (optional)
5. **cta** (admissions / inquiry)

**Example block props**

Hero
```json
{
  "title": "Ifitwala Secondary School",
  "subtitle": "Home of the Brave",
  "images": [],
  "autoplay": true,
  "interval": 6000,
  "cta_label": "Book a Visit",
  "cta_link": "/admissions"
}
```

Rich text
```json
{
  "content_html": "<p>Welcome to Ifitwala Secondary School — a community where curiosity, discipline, and care meet.</p>",
  "max_width": "normal"
}
```

Program list
```json
{
  "school_scope": "current",
  "show_intro": true,
  "card_style": "standard",
  "limit": 6
}
```

Leadership
```json
{
  "title": "Leadership & Administration",
  "roles": ["Head", "Principal"],
  "limit": 6
}
```

CTA
```json
{
  "title": "Ready to apply?",
  "text": "Start your admissions journey today.",
  "button_label": "Apply Now",
  "button_link": "https://apply.school.edu"
}
```

---

## 2) About Page

**Route input:** `about`

**Suggested block order**

1. **hero** (short)
2. **rich_text** (history + mission)
3. **leadership**
4. **cta**

**Example block props**

Hero
```json
{
  "title": "About Us",
  "subtitle": "A tradition of excellence, rooted in care",
  "images": []
}
```

Rich text
```json
{
  "content_html": "<h2>Our History</h2><p>Founded in 1998, we serve learners from diverse backgrounds.</p><h2>Mission</h2><p>We build confident, compassionate learners.</p>",
  "max_width": "wide"
}
```

Leadership
```json
{
  "title": "Leadership & Administration",
  "roles": ["Head", "Principal"],
  "limit": 12
}
```

CTA
```json
{
  "title": "Meet our campus",
  "text": "Schedule a tour to see the school in action.",
  "button_label": "Book a Visit",
  "button_link": "/admissions"
}
```

---

## 3) Admissions Page

**Route input:** `admissions`

**Suggested block order**

1. **hero**
2. **rich_text** (process steps)
3. **program_list** (if admissions by program)
4. **cta** (apply / inquiry)

**Example block props**

Hero
```json
{
  "title": "Admissions",
  "subtitle": "A clear, supportive application process",
  "images": [],
  "cta_label": "Start Application",
  "cta_link": "https://apply.school.edu"
}
```

Rich text
```json
{
  "content_html": "<ol><li>Submit inquiry</li><li>Schedule a visit</li><li>Complete application</li><li>Receive decision</li></ol>",
  "max_width": "narrow"
}
```

Program list (optional)
```json
{
  "school_scope": "current",
  "show_intro": false,
  "card_style": "standard",
  "limit": 6
}
```

CTA
```json
{
  "title": "Questions?",
  "text": "Our admissions team is here to help.",
  "button_label": "Contact Admissions",
  "button_link": "/contact"
}
```

---

## 4) Notes & Tips

* **Carousel images**: leave `hero.images` empty to use `School.gallery_image`.
* **CTA links**: must start with `/` or `https://`.
* **Program list**: only shows programs offered by the school (via Program Offering).
* **Leadership**: only shows employees flagged for website visibility.
* **Build**: content edits do not require a build; only CSS/template edits do.
* **School-scoped routes**: page links should use canonical `full_route` (for example `/{school_slug}/about`) when linking between public school pages.

---

## 5) Fresh Install Default Scaffold

For a new site, the bootstrap flow seeds these pages for the default website school:

1. route `/` (home)
2. route `about`
3. route `admissions`
4. route `programs`

All four pages are created as `School Website Page` records with canonical `full_route` values and schema-valid default blocks, so the public website has immediate structure and navigation without manual Desk setup.
