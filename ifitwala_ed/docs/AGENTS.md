File: ifitwala_ed/docs/AGENTS.md

# AGENTS.md — Documentation Local Rules

This file adds local rules for work inside `ifitwala_ed/docs/`.
The root `AGENTS.md` remains authoritative and must still be obeyed.

This folder is authoritative for architecture, behavior, and contract documentation.

---

## 0. Local Mission

Inside `ifitwala_ed/docs/`, prioritize:

1. documentation as source of truth
2. one canonical contract per feature
3. explicit status and code references
4. drift prevention
5. documentation that helps both humans and coding agents

Docs must reflect reality, not aspiration.

## 0.1 Local Environment Note

- This Codex session is on the user's local machine inside the repo.
- Do not add repetitive environment caveats about `.venv`, `frappe`, `bench`, or local shell `PATH` unless a specific verification attempt failed and the exact failure is needed for accuracy.

---

## 1. Canonical Documentation Rule

Each feature should have one canonical contract document.

Do not mix:

- locked behavior
- brainstorm text
- speculative notes
- draft ideas

If exploratory content is needed, keep it in a separate non-authoritative file.

Canonical docs must be clearly usable by:

- developers
- reviewers
- coding agents
- future maintainers

## 1.1 Documentation Routing Index Rule

When a docs folder contains multiple current notes or a mix of canonical and historical/proposal material, maintain a local `README.md` index.

That index must:

- say what the folder covers
- identify the current canonical docs
- give a recommended read order
- call out non-authoritative files explicitly

The index is navigation only.
Do not restate full contracts inside it.

When a folder has a `README.md`, agents should read it before scanning individual docs.

---

## 2. Status Marker Rule

Each major feature section should include clear status markers where applicable:

- `Status`
- `Code refs`
- `Test refs`

Avoid vague prose that does not map to implementation.

If a section cannot point to code or tests, say so explicitly.

---

## 3. Drift Control Rule

When approved implementation changes behavior:

- update the relevant canonical doc in the same change
- update the local docs-folder `README.md` too when the canonical set or read order changed
- do not silently leave stale behavior text
- do not delete old contract text unless it is truly superseded
- if old content is replaced, mark it deprecated or point to the replacement

Drift is a bug.

---

## 4. Contract Clarity Rule

Docs must be explicit enough that a coding agent can tell:

- which files own the behavior
- which layer owns the invariant
- whether logic belongs in:
  - DocType/controller
  - API endpoint
  - SPA surface
  - scheduler/background job
  - report/dashboard
- what must not be reimplemented elsewhere
- for governed file/image reads, which surface owns the visibility contract and which API resolves the display/open URL

If a doc is too vague to guide safe implementation, improve the doc first.

For the governed file/link/attachment architecture specifically, keep the canonical read path explicit in docs:

- `files_and_policies/README.md`
- `files_and_policies/files_01_architecture_notes.md`
- `files_and_policies/files_03_implementation.md`
- `files_and_policies/files_07_education_file_semantics_and_cross_app_contract.md`
- `files_and_policies/files_08_cross_portal_governed_attachment_preview_contract.md`
- `../ifitwala_drive/ifitwala_drive/docs/06_api_contracts.md` when the note describes the Ed/Drive seam

---

## 5. Product / Security / Concurrency Coverage Rule

Canonical feature docs should explicitly state, where relevant:

- UX goals and friction reduction expectations
- permission and scope constraints
- multi-tenant isolation expectations
- concurrency/performance expectations
- queue/cache/realtime expectations when those are part of the design
- whether queue names are semantic-only or must exist in the live worker topology, and where enqueue-time normalization or fallback ownership lives
- permission-matrix expectations for governed file/image access when a surface exposes private media

Do not leave these as implicit assumptions for critical workflows.

---

## 6. Markdown Structure Rules

For docs under `ifitwala_ed/docs/docs_md/`:

- include YAML front matter with:
  - `version`
  - `last_change_date`
- update both on every change
- if the file documents a DocType, it must include a top-level `## Permission Matrix`
- when the DocType inherits permissions from a parent (for example child tables), document that inherited model inside `## Permission Matrix` instead of omitting the section
- `## Related Docs` should appear immediately before `## Technical Notes (IT)` when that section exists
- `## Technical Notes (IT)` must be the final top-level section
- `## Technical Notes (IT)` is reserved for administrator and system-admin implementation detail, not general product guidance
- preserve figure tags exactly

Do not break the existing docs pipeline conventions.

---

## 7. Reality-First Rule

Do not document hoped-for architecture as if it already exists.

Be precise about status:

- Implemented
- Partial
- Planned
- Deprecated

If implementation and docs disagree, stop and resolve the mismatch explicitly.

---

## 8. Documentation Delivery Checklist

Before finalizing a docs change, verify:

- the doc is canonical or clearly marked otherwise
- behavior described matches code reality
- code refs are concrete
- test refs are concrete or explicitly absent
- product/security/concurrency constraints are documented where relevant
- status is honest
- obsolete sections are retired or deprecated cleanly
- formatting/front matter/section-order rules remain valid

---

## 9. High Concurrency Documentation Rule

For any hot-path, dashboard, workspace, or SPA-supporting feature doc, the canonical concurrency note is:

- `ifitwala_ed/docs/high_concurrency_contract.md`

Docs must not describe request-heavy, cache-unsafe, or client-waterfall designs as acceptable if they conflict with that note.

When documenting Drive or file-related UX in Ifitwala_Ed, explicitly state:

- whether the surface is context-first or browse-first
- whether the endpoint is bootstrap, read-model, or mutation
- how many foundational calls the SPA is expected to make
- whether preview/download uses Drive grants instead of raw URLs

---

## 10. User-Centric Documentation Style (docs/docs_md/)

Files under `docs/docs_md/` are **end-user documentation**. They must be written for the people actually using Ifitwala Ed—teachers, administrators, admissions staff, principals—not just developers.

### 10.1 Target Audience

Write for:
- **System Administrators** setting up the platform
- **Academic Staff** using features day-to-day
- **School Leadership** making configuration decisions
- **Operational Staff** who are not technical

Do NOT write for:
- Software developers (that's what code comments and architecture docs are for)
- Frappe framework experts

### 10.2 Tone and Voice

| Do This | Not This |
|---------|----------|
| Conversational and helpful | Dry, technical, academic |
| "You can create..." "Your schools will..." | "The system implements..." "The DocType enforces..." |
| Explain *why* it matters | Just list *what* it does |
| Use real examples | Use abstract descriptions |
| Celebrate differentiators | Be neutral about capabilities |
| Anticipate user questions | Assume they already understand |

### 10.3 Document Structure

Every `docs_md` DocType document should follow this structure:

1. **Opening Hook** — What is this? Why does it matter? (1-2 paragraphs)
2. **Why This Matters** — Bullet points explaining practical value
3. **Creating/Using [DocType]** — Step-by-step practical guide
4. **Field Reference** — Table explaining what each field does, with tips
5. **Where You'll Use This** — Real workflows and scenarios
6. **Permissions: Who Can Do What** — Second-level section (##) with role table
7. **Best Practices** — Actionable advice for different scenarios
8. **Common Questions** — FAQ format addressing likely confusion points
9. **Related Docs** — Links to connected features
10. **Technical Notes (IT)** — Final section for system administrators

### 10.4 Key Content Elements

**Include marketing positioning where appropriate:**
- Call out why Ifitwala Ed's approach is different/better
- Use callout boxes for differentiators
- Don't be afraid to sell the platform's depth

**Make it practical:**
- Step-by-step instructions, not just feature lists
- Real-world scenarios (single school vs. multi-campus vs. international group)
- Tips for common situations
- Warnings about gotchas

**Make it accessible:**
- Define technical terms when first used
- Use tables for comparisons and role matrices
- Use bullet points for scannable content
- Include a FAQ section

### 10.5 Permission Matrix Placement

The `## Permissions: Who Can Do What` section (or similarly named) **must be a second-level heading** (`##`), not buried at the end. Users need to understand access control early.

Include:
- What each role can do (in plain language)
- Typical job titles for each role
- How scoping/isolation works (if relevant)

### 10.6 Reference Document

See `organization.md` as the canonical example of this style:
- Conversational tone throughout
- "Why Ifitwala Ed is different" callouts
- Step-by-step creation guide
- Real-world scenarios (single school, group, multi-national)
- Practical FAQ
- Permission section as `##` (second level)
- Technical details relegated to final section

When writing or rewriting any `docs_md` file, use `organization.md` as your style reference.

---

## 11. Custom Block Components (docs/docs_md/)

The documentation system supports custom JSX-style blocks for richer presentation. Use these instead of plain markdown for better user experience.

### 11.1 Steps Block

Use `<Steps>` with nested `<Step>` entries for procedural instructions. Each step can include a `title` attribute.

```markdown
<Steps title="Setting up your Organization">
  <Step title="Navigate to Setup">
    Go to **Setup > Organization**, then click **New**.
  </Step>
  <Step title="Enter Basic Information">
    Fill in the Organization Name and Abbreviation.
  </Step>
</Steps>
```

**When to use:**
- Creation/setup workflows
- Multi-step processes
- Lifecycle explanations

### 11.2 Do / Don't Block

Use `<DoDont>` with nested `<Do>` and `<Dont>` entries for guidance on best practices.

```markdown
<DoDont doTitle="Do" dontTitle="Don't">
  <Do>Create an Organization even for single schools.</Do>
  <Do>Use meaningful abbreviations.</Do>
  <Dont>Create separate Organizations for each campus.</Dont>
  <Dont>Change the abbreviation frequently.</Dont>
</DoDont>
```

**When to use:**
- Best practices sections
- Common pitfalls to avoid
- Quick guidance without lengthy explanations

### 11.3 Related Docs Block

Use `<RelatedDocs>` to render related document cards. The `slugs` attribute accepts comma-separated slugs.

```markdown
<RelatedDocs
  slugs="school,institutional-policy,student-applicant"
  title="Continue With Related Setup Docs"
/>
```

**When to use:**
- End of documents (instead of markdown link lists)
- "See also" sections
- Navigation to related workflows

### 11.4 Callout Block

Use `<Callout>` for highlighted information boxes.

```markdown
<Callout type="info" title="Why Ifitwala Ed is different">
  Unlike platforms that treat each school as an isolated silo...
</Callout>

<Callout type="warning" title="Enterprise-grade security">
  This is architectural isolation that most platforms don't have...
</Callout>

<Callout type="tip" title="What happens automatically">
  The moment you save, Ifitwala Ed creates a complete Chart of Accounts...
</Callout>
```

**Available types:** `info`, `warning`, `tip`, `success`, `error`

**When to use:**
- Differentiators and marketing positioning (`type="info"`)
- Important warnings (`type="warning"`)
- Helpful tips (`type="tip"`)
- Positive confirmations (`type="success"`)
- Critical errors to avoid (`type="error"`)

### 11.5 Block Usage Guidelines

| Block | Location | Purpose |
|-------|----------|---------|
| `Steps` | After "Creating/Using" heading | Step-by-step procedures |
| `DoDont` | Inside "Best Practices" section | Quick do/don't guidance |
| `RelatedDocs` | Before "Technical Notes (IT)" | Navigation to related docs |
| `Callout` | Anywhere emphasis is needed | Highlighted information |

**Formatting tips:**
- Use sentence case for Step titles and Callout titles
- Keep Step content to 1-3 sentences
- Limit DoDont lists to 4-6 items per side
- Always include a `title` attribute for Steps and Callouts
- Use RelatedDocs instead of markdown bullet lists for related links
