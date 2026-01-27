# School Slug vs Website Page Route (Canonical)

**Audience:** Website admins, implementers, and content editors
**Scope:** Builder-lite public website routing

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

### 1.2 `School Website Page.route` (page path)

**What it is**

* The **page path input** used by website managers
* Stored as a **canonical full route** after auto-prefixing
* Identifies **which page** to render for that school

**Where it lives**

* DocType: `School Website Page`
* Field: `route`

---

## 2. The hard rule (enforced)

**Route input is always relative to the school.**

You do **not** type the school slug. The system adds it behind the scenes.

If `School.website_slug = iss`:

| User input (route) | Stored route (canonical) |
| --- | --- |
| `admissions` | `/iss/admissions` |
| `/admissions` | `/iss/admissions` |
| `academics/programs` | `/iss/academics/programs` |
| `/` or empty | `/iss` |
| `/iss` | `/iss/iss` (because input is treated as relative) |

**Important:** If you type `/iss`, it becomes `/iss/iss` by design. The slug is never a user input.

---

## 3. Root page behavior

If the route is **empty** or `/`, the system creates the **school root page**:

```
/iss
```

A clear message is shown to the user on save.

---

## 4. Routing resolution model (how requests are matched)

When a request comes in:

1. The **first path segment** is used to resolve the school by `website_slug`
2. The full path is matched against `School Website Page.route`
3. The page is rendered for that school

Because routes are stored with the slug prefix, the resolver is deterministic and safe.

---

## 5. Practical examples

### Example A - Home page for a school

```
School.website_slug: iss
User input route: /
Stored route: /iss
```

### Example B - Admissions page for the same school

```
School.website_slug: iss
User input route: admissions
Stored route: /iss/admissions
```

### Example C - Another school on the same site

```
School.website_slug: iis
User input route: admissions
Stored route: /iis/admissions
```

These are **different schools** and must not share routes.

---

## 6. Why this separation exists

* `website_slug` is **school identity**
* `route` is **page identity input**, then normalized into a canonical route

This allows:

* multiple pages per school
* clear SEO-friendly URL structure
* predictable school scoping

It is **not** a duplicate source of truth - it is a hierarchy:

```
School identity (slug)
  -> Page identity (route)
```

---

## 7. Implementation guardrail

The `School Website Page` DocType:

* reads the school slug
* prefixes it to the input route
* stores the canonical route

This makes the slug the single source of truth for routing and prevents mis-routing.

---

## 8. Summary (one-line rule)

> **School slug identifies the school; page route is a relative path that is auto-prefixed with the slug.**

---
