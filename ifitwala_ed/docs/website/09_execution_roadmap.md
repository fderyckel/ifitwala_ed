<!-- ifitwala_ed/docs/website/09_execution_roadmap.md -->
# Website Module Execution Roadmap (Prioritized)

**Status:** Proposed execution plan  
**Scope:** `ifitwala_ed` website module (DocTypes, renderer, providers, Desk editor UX, marketing workflows)  
**Goal:** Reduce friction and cognitive load for school marketing and website managers while preserving server-side invariants

---

## 0) What this roadmap optimizes

1. Editor clarity over flexibility chaos
2. Save-time validation over render-time surprises
3. One canonical contract source over doc/code drift
4. Marketing intent workflows over technical plumbing
5. School-brand personalization without tenant code execution

---

## 1) Delivery phases

## Phase A (0-2 weeks) - Quick wins with immediate friction reduction

### A1. Canonical contract lock (single source of truth)

**Outcome**
- Block schemas and metadata are defined once and reused by setup seed + validation + editor.

**Files**
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/setup/setup.py`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/website/renderer.py`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/public/js/website_props_builder.js`
- New: `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/website/block_registry.py`
- Docs sync:
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/docs/website/03_website_pages_provider.md`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/docs/website/04_builder_lite_plan.md`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/docs/website/06_block_props_guide.md`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/docs/website/08_phase02_plan.md`

**Risk**
- Existing records with stale schemas can fail validation if strict mode is immediate.

### A2. Save-time validation moved from renderer to DocTypes

**Outcome**
- Editors see blocking errors on save, not later during preview/live render.

**Files**
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/school_website_page/school_website_page.py`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/program_website_profile/program_website_profile.py`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/website_story/website_story.py`
- New shared validator:
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/website/validators.py`

**Risk**
- Invalid legacy pages must be remediated or auto-normalized.

### A3. Block registry governance lock

**Outcome**
- `Website Block Definition` becomes system-owned in practice, not only by convention.

**Files**
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/website_block_definition/website_block_definition.json`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/website_block_definition/website_block_definition.py`

**Risk**
- Existing Website Manager/Marketing users lose direct edit access (intentional).

---

## Phase B (2-5 weeks) - Editor UX stabilization

### B1. Context-aware block picker and guardrails

**Outcome**
- Only valid blocks for page context are shown; lower cognitive load and fewer failed saves.

**Files**
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/public/js/website_props_builder.js`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/school_website_page/school_website_page.js`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/program_website_profile/program_website_profile.js`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/website_story/website_story.js`

**Risk**
- Requires careful backward compatibility for existing records.

### B2. Real SEO assistant sidebar

**Outcome**
- Editors get immediate actionable warnings: H1 ownership, meta lengths, OG image, missing CTA, schema readiness.

**Files**
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/school_website_page/school_website_page.js`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/program_website_profile/program_website_profile.js`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/website_story/website_story.js`
- New server helper:
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/website/seo_checks.py`

**Risk**
- Keep warnings non-blocking except hard invariants.

---

## Phase C (5-8 weeks) - Marketing and website-manager workflows

### C1. Publishing workflow with review states

**Outcome**
- Marketing managers can collaborate safely: `Draft -> In Review -> Approved -> Published`.

**Files**
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/school_website_page/school_website_page.json`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/school_website_page/school_website_page.py`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/program_website_profile/program_website_profile.json`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/program_website_profile/program_website_profile.py`
- New workflow files (if adopted):
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/workflow/website_page_review/`

**Risk**
- Must remain consistent with current auto-derived publication status rules.

### C2. Snippet model fix for scoped overrides + role access

**Outcome**
- School/org/global snippets behave as intended and are editable by marketing users.

**Files**
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/website_snippet/website_snippet.json`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/website_snippet/website_snippet.py`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/website/providers/content_snippet.py`

**Risk**
- Needs safe migration from globally unique `snippet_id`.

---

## Phase D (8-12 weeks) - Feature expansion for visual quality and conversion

### D1. School theme profiles (K-12 and college presets)

**Outcome**
- Brand personalization (color, type scale, spacing density, hero style) without custom CSS injection.

**Files**
- New DocType:
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/website_theme_profile/`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/website/templates/page.html`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/public/website/website.css`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/website/renderer.py`

**Risk**
- Must preserve Tailwind scoping and no cross-surface leakage.

### D2. Visual enhancement module (non-critical JS layer)

**Outcome**
- Better motion and presentation (carousel polish, stagger reveals, CTA emphasis) while keeping content server-rendered.

**Files**
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/public/website/website.js`
- New optional scripts by block:
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/public/website/blocks/*.js`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/setup/setup.py` (block `script_path` seeding)

**Risk**
- Must remain enhancement-only; no data dependencies in JS.

### D3. Marketing analytics events and attribution

**Outcome**
- Website managers track CTA performance by intent, page, and school.

**Files**
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/website/blocks/admission_cta.html`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/public/website/website.js`
- New server endpoint/service:
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/website/analytics.py`
- New reporting view:
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/report/website_cta_performance/`

**Risk**
- Enforce privacy-safe collection and low-latency write path.

---

## 2) Migration patch queue (proposed)

Create new patch package:
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/patches/website/`
- Register patches in `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/patches.txt`

Patch order:
1. `ifitwala_ed.patches.website.p01_seed_block_registry_from_code`
2. `ifitwala_ed.patches.website.p02_lock_block_definition_permissions`
3. `ifitwala_ed.patches.website.p03_backfill_page_block_orders_and_missing_props`
4. `ifitwala_ed.patches.website.p04_validate_and_normalize_legacy_block_props`
5. `ifitwala_ed.patches.website.p05_add_workflow_fields_website_pages`
6. `ifitwala_ed.patches.website.p06_backfill_workflow_state_from_status`
7. `ifitwala_ed.patches.website.p07_refactor_snippet_uniqueness_to_scoped`
8. `ifitwala_ed.patches.website.p08_rebuild_snippet_scope_indexes`
9. `ifitwala_ed.patches.website.p09_seed_theme_profiles_k12_college`
10. `ifitwala_ed.patches.website.p10_backfill_tracking_ids_for_admission_cta`

---

## 3) Testing plan per phase

### Automated
- Add unit tests:
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/school_website_page/test_school_website_page.py`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/program_website_profile/test_program_website_profile.py`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/website_snippet/test_website_snippet.py`
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/school_site/doctype/website_block_definition/test_website_block_definition.py`
- New renderer tests:
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/website/tests/test_renderer.py`
- New provider tests:
- `/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/website/tests/test_providers.py`

### Manual acceptance
1. Marketing user can create/edit/publish without raw JSON edits for common flows.
2. Invalid blocks fail on save with clear errors.
3. Preview never succeeds for invalid SEO/H1 state.
4. Program cards only show school-offered, published, non-archived programs.
5. Snippet scope resolution works in school -> organization -> global order.

---

## 4) Dependency and approval gates

1. **Gate 1 (before schema changes):** approve workflow/status model for website docs.
2. **Gate 2 (before permission changes):** approve role matrix for Website Manager vs Marketing User.
3. **Gate 3 (before analytics):** approve event schema and data retention policy.

---

## 5) 10 original proposals mapped to execution

1. Canonical contract source and sync tooling -> Phase A1  
2. Save-time validation engine -> Phase A2  
3. Block registry governance lock -> Phase A3  
4. Context-aware block picker -> Phase B1  
5. SEO assistant for editors -> Phase B2  
6. Publishing workflow for marketing teams -> Phase C1  
7. Scoped snippet model and permissions -> Phase C2  
8. Theme profiles for K-12/college personalization -> Phase D1  
9. Visual enhancement JS module (non-critical) -> Phase D2  
10. Marketing analytics and conversion reporting -> Phase D3

---

## 6) Recommended start sequence (highest ROI)

1. Phase A1
2. Phase A2
3. Phase B1
4. Phase B2
5. Phase C1

This sequence removes the largest daily editor pain before introducing new surface area.
