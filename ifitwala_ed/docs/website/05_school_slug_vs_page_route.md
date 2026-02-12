<!-- ifitwala_ed/docs/website/05_school_slug_vs_page_route.md -->
# School Slug vs Website Page Route (Canonical)

**Audience:** Website admins, implementers, and content editors
**Scope:** Builder-lite public website routing
**Status (February 12, 2026):** Implemented and enforced by `School Website Page` server validation and renderer resolution

---

## 0. Root route ownership (`/`)

The public root route `/` is resolved through Organization:

* `Organization.default_website_school` points to the school that owns `/`
* The selected school **must belong to that Organization**
* Renderer rewrites `/` to that school root route (`/{school_slug}`)
* Legacy public entry aliases `/home`, `/index`, and `/index.html` are normalized to `/`
* Desk entry `/app` is not a public website route and is handled outside website page resolution

This keeps organization-level governance while preserving school-scoped page identity.

---

## 1. Two different concepts (do not mix them)

### 1.1 `School.website_slug` (identity)

**What it is**

* The unique URL identity for a school
* Used to **resolve which school** a request belongs to

**Where it lives**

* DocType: `School`
* Field: `website_slug`

**Example**

```
School: Ifitwala Secondary School
website_slug: iss
```

This means the school is addressable under routes that start with `/iss`.

---

### 1.2 `School Website Page.route` (page path input)

**What it is**

* The **page path input** typed by website managers
* Stored **exactly as entered** (no auto-prefixing)

**Rules (enforced)**

* `/` is **only** for the school home page
* All other pages must be entered **without a leading `/`**
  * Examples: `about`, `admissions`, `about/team`
* No trailing `/`
* No empty segments (`//`)
* Do **not** include the school slug

**Where it lives**

* DocType: `School Website Page`
* Field: `route`

---

### 1.3 `School Website Page.full_route` (canonical)

**What it is**

* The **canonical full route** used for routing and rendering
* Computed by the system from `School.website_slug` + `route`
* Visible but **read-only**

**Where it lives**

* DocType: `School Website Page`
* Field: `full_route`

---

## 2. The hard rule (enforced)

**Route input is always relative to the school.**

You do **not** type the school slug. The system builds the canonical full route behind the scenes.

If `School.website_slug = iss`:

| User input (`route`) | Stored `route` | Stored `full_route` |
| --- | --- | --- |
| `/` | `/` | `/iss` |
| `admissions` | `admissions` | `/iss/admissions` |
| `about/team` | `about/team` | `/iss/about/team` |

**Invalid inputs**

* `/admissions` (leading `/` not allowed for non-root)
* `iss/admissions` (school slug is never part of the input)
* `admissions/` (trailing `/` not allowed)

---

## 3. Root page behavior

If the route is `/`, the system creates the **school root page**:

```
/iss
```

Only one root page is allowed per school.

---

## 4. Routing resolution model (how requests are matched)

When a request comes in:

1. The **first path segment** is used to resolve the school by `website_slug`
2. The full path is matched against `School Website Page.full_route`
3. The page is rendered for that school

Because routes are stored in `full_route` with the slug prefix, the resolver is deterministic and safe.

---

## 5. Practical examples

### Example A - Home page for a school

```
School.website_slug: iss
User input route: /
Stored full_route: /iss
```

### Example B - Admissions page for the same school

```
School.website_slug: iss
User input route: admissions
Stored full_route: /iss/admissions
```

### Example C - A nested page

```
School.website_slug: iss
User input route: about/team
Stored full_route: /iss/about/team
```

---

## 6. Why this separation exists

* `website_slug` is **school identity**
* `route` is **page identity input** (user-owned)
* `full_route` is **canonical routing identity** (system-owned)

This allows:

* multiple pages per school
* clear SEO-friendly URL structure
* predictable school scoping

---

## 7. Implementation guardrail

The `School Website Page` DocType:

* reads the school slug
* computes `full_route`
* never overwrites the user-entered `route`

---

## 8. Summary (one-line rule)

> **`/` resolves via Organization.default_website_school; school slug identifies school pages; route is user input; full_route is canonical.**

---
