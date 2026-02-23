<!-- ifitwala_ed/docs/website/05_school_slug_vs_page_route.md -->
# School Slug vs Website Page Route (Canonical)

**Audience:** Website admins, implementers, and content editors
**Scope:** Builder-lite public website routing
**Status (February 13, 2026):** Implemented and enforced by route rules, renderer resolution, and `School Website Page` validation

---

## 0. Root route ownership (`/`)

The public root route `/` is the **Organization Landing**.

* `/` is not rewritten to a default school anymore.
* Legacy aliases `/home`, `/index`, and `/index.html` resolve to the same landing.
* School websites are scoped under `/schools/...`.
* Desk entry `/app` remains framework-owned and outside website page resolution.

This keeps organization-level discovery separate from school-level website pages.

---

## 1. Two different concepts (do not mix them)

### 1.1 `School.website_slug` (identity)

**What it is**

* The unique URL identity for a school
* Used to resolve which school owns `/schools/{school_slug}/...`

**Where it lives**

* DocType: `School`
* Field: `website_slug`

**Example**

```
School: Ifitwala Secondary School
website_slug: iss
```

This means the school home is `/schools/iss`.

---

### 1.2 `School Website Page.route` (page path input)

**What it is**

* The page path input typed by website managers
* Stored exactly as entered (no slug prefixing)

**Rules (enforced)**

* `/` is only for the school home page
* All other pages must be entered without a leading `/`
  * Examples: `about`, `admissions`, `about/team`
* No trailing `/`
* No empty segments (`//`)
* Do not include the school slug

**Where it lives**

* DocType: `School Website Page`
* Field: `route`

---

### 1.3 `School Website Page.full_route` (canonical)

**What it is**

* The canonical route used for matching and rendering
* Computed by the system from `School.website_slug` + `route`
* Read-only and system-owned

**Where it lives**

* DocType: `School Website Page`
* Field: `full_route`

---

## 2. The hard rule (enforced)

Route input is always school-relative, and canonical full routes are always under `/schools/{school_slug}`.

If `School.website_slug = iss`:

| User input (`route`) | Stored `route` | Stored `full_route` |
| --- | --- | --- |
| `/` | `/` | `/schools/iss` |
| `admissions` | `admissions` | `/schools/iss/admissions` |
| `about/team` | `about/team` | `/schools/iss/about/team` |

**Invalid inputs**

* `/admissions` (leading `/` not allowed for non-root)
* `iss/admissions` (school slug is never part of the input)
* `admissions/` (trailing `/` not allowed)

---

## 3. Root page behavior

If the route is `/`, the system creates the school home page:

```
/schools/{school_slug}
```

Only one root page is allowed per school.

---

## 4. Routing resolution model

For school website requests:

1. `/schools/{school_slug}/...` resolves the school by `website_slug`
2. Full path is matched against `School Website Page.full_route`
3. The page is rendered for that school

For organization landing requests:

1. `/` (and aliases) render the organization landing page
2. Landing lists published schools with valid `website_slug`

For admissions/public form requests:

1. `/apply/inquiry` and `/apply/registration-of-interest` are native Web Form routes.
2. Legacy `/inquiry` and `/registration-of-interest` only redirect to those canonical `/apply/*` routes.
3. Admissions applicant SPA is namespaced under `/admissions/*` and does not own `/apply/*`.

For authenticated portal requests:

1. Canonical authenticated portal namespace is `/portal/*`.

---

## 5. Summary (one-line rule)

> **`/` is organization landing; school pages live under `/schools/{school_slug}/...`; `route` is user input; `full_route` is canonical.**
