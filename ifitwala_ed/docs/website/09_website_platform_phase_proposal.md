<!-- ifitwala_ed/docs/website/09_website_platform_phase_proposal.md -->
# Website Platform Phase Proposal

This note is a non-authoritative proposal.

Current canonical runtime remains defined by:

- `ifitwala_ed/docs/website/01_architecture_notes.md`
- `ifitwala_ed/docs/website/03_website_pages_provider.md`
- `ifitwala_ed/docs/website/05_school_slug_vs_page_route.md`
- `ifitwala_ed/docs/website/06_block_props_guide.md`
- `ifitwala_ed/docs/website/08_course_catalog_contract.md`
- `ifitwala_ed/docs/files_and_policies/files_05_organization_media_governance.md`
- `ifitwala_ed/docs/high_concurrency_contract.md`

This proposal exists to define a phased implementation path before schema changes, cross-module behavior changes, or broad public-site governance changes are approved.

## 1. Decision Goal

Status: Planned
Code refs: `ifitwala_ed/website/block_registry.py`, `ifitwala_ed/website/renderer.py`, `ifitwala_ed/website/providers/*.py`, `ifitwala_ed/school_site/doctype/school_website_page/*`, `ifitwala_ed/public/js/website_props_builder.js`
Test refs: `ifitwala_ed/school_site/doctype/school_website_page/test_school_website_page.py`, `ifitwala_ed/website/tests/test_leadership_provider.py`

Target product outcome:

1. Ifitwala_Ed ships one coherent school-website platform, not a collection of one-off blocks.
2. The default product experience is optimized for independent schools, while still supporting organizations with multiple schools or divisions.
3. Public staff content uses `Employee` as the source of truth.
4. Public staff presentation supports leadership, teachers, counselors, operational staff, and other website-visible employee groups without duplicating identity logic.
5. Personal pages remain optional, not mandatory, and are layered on top of a stronger directory/profile system.
6. Public website scope remains exact-school by default, with explicit and bounded cross-school inclusion only where the contract allows it.
7. Accessibility, media governance, performance, and editorial workflow are treated as first-class platform requirements rather than post-launch clean-up.

The product goal is simple:

`school-first website foundation -> canonical people/directory platform -> reusable dynamic modules -> multi-site governance -> operational excellence`

## 2. Positioning Decisions For This Proposal

Status: Planned
Code refs: `ifitwala_ed/docs/website/01_architecture_notes.md`, `ifitwala_ed/docs/website/03_website_pages_provider.md`, `ifitwala_ed/docs/setup/school_organization_scope_contract.md`, `ifitwala_ed/docs/nested_scope_contract.md`
Test refs: `ifitwala_ed/utilities/test_school_tree.py`, `ifitwala_ed/website/tests/test_leadership_provider.py`

This proposal adopts the following product decisions:

### 2.1 Customer shape

- most customers are expected to be independent schools
- the platform must still work for multi-school organizations and divisions/campuses
- the default authoring and rendering path should therefore be school-first, not district-first

### 2.2 Public people source of truth

- `Employee` remains the public staff identity source of truth
- the website may add a website-owned public presentation layer, but it must not replace `Employee` as identity truth
- public profile logic must not reimplement HR identity ownership

### 2.3 Public scope model

- school websites remain exact-school by default
- parent-school or organization surfaces may opt into descendant inclusion only through explicit module rules
- if mixed-school records appear, the UI must label school ownership clearly
- silent descendant inheritance is treated as a UX defect on public school pages

### 2.4 Personal pages

- personal pages are optional
- the canonical public people experience should be a directory + rich profile system first
- personal pages should be an extension of the same people model, not a second content system

## 3. Current Baseline In Code

Status: Implemented baseline
Code refs: `ifitwala_ed/website/renderer.py`, `ifitwala_ed/website/block_registry.py`, `ifitwala_ed/website/providers/leadership.py`, `ifitwala_ed/website/providers/program_list.py`, `ifitwala_ed/website/providers/course_catalog.py`, `ifitwala_ed/utilities/image_utils.py`, `ifitwala_ed/hooks.py`
Test refs: `ifitwala_ed/website/tests/test_leadership_provider.py`, `ifitwala_ed/website/tests/test_program_list_provider.py`, `ifitwala_ed/website/tests/test_course_catalog_provider.py`, `ifitwala_ed/utilities/test_employee_image_utils.py`

Today the product already has:

- locked website routing under `/schools/...`
- `School Website Page` with block-based authoring
- trusted provider-driven rendering
- workflow states for page publication
- governed image variants for employee images
- baseline leadership, program, and course website surfaces

What is still missing for a top-tier school CMS platform:

- one canonical public people/directory system
- reusable dynamic modules for calendars, alerts, news, and documents with stronger editorial reuse
- explicit public-scope governance across school, parent-school, and organization surfaces
- stronger editor operations, scheduled publishing, expiry, and ownership
- accessibility and performance operations at platform level

## 4. Implementation Principles For This Roadmap

Status: Planned
Code refs: `ifitwala_ed/docs/website/01_architecture_notes.md`, `ifitwala_ed/docs/website/03_website_pages_provider.md`, `ifitwala_ed/docs/files_and_policies/files_05_organization_media_governance.md`, `ifitwala_ed/docs/high_concurrency_contract.md`
Test refs: `None`

The following principles should govern every phase:

1. Build foundations before new page types.
2. Prefer one canonical contract per module over special-case block behavior.
3. Keep school-first exact scope as the default public rule.
4. Make cross-school syndication explicit and reviewable.
5. Keep `Employee` as truth and layer website presentation on top.
6. Use governed media derivatives and server-owned display contracts only.
7. Treat accessibility, performance, and cache invalidation as product requirements.
8. Avoid new module work that bypasses the provider/contract architecture already locked in website docs.

## 5. Phase 0 — Foundation Contracts

Status: Planned, highest priority
Code refs: `ifitwala_ed/website/block_registry.py`, `ifitwala_ed/website/renderer.py`, `ifitwala_ed/website/providers/leadership.py`, `ifitwala_ed/school_site/doctype/school_website_page/*`, `ifitwala_ed/utilities/image_utils.py`, `ifitwala_ed/public/js/website_props_builder.js`
Test refs: `ifitwala_ed/school_site/doctype/school_website_page/test_school_website_page.py`, `ifitwala_ed/website/tests/test_leadership_provider.py`, `ifitwala_ed/utilities/test_employee_image_utils.py`

This phase exists to prevent drift and rework.
No broad website expansion should happen before these contracts are approved.

### 5.1 Deliverables

1. One canonical public people contract.
   - define public identity ownership
   - define which fields come from `Employee`
   - define which fields may be website-owned presentation fields
   - define public/private visibility rules for employee data

2. One canonical public scope contract for website modules.
   - exact-school default
   - explicit descendant inclusion model
   - depth control rules
   - labeling rules when mixed-school results are rendered

3. One canonical media/performance contract for public people and cards.
   - derivative-first image loading
   - responsive `srcset` use
   - per-surface image-size expectations
   - cache invalidation ownership

4. One canonical editorial governance contract.
   - authoring ownership
   - review/publish permissions
   - preview rules
   - scheduled publish/expiry expectations

5. One reusable website module contract template.
   - required sections for future modules
   - product/security/concurrency expectations
   - code ownership expectations

### 5.2 Intentionally undecided in this phase

The following should remain intentionally undecided until schema review:

- exact name of any new website-owned employee profile DocType
- exact field names for public profile overrides
- exact field placement for scheduled publish/expiry if workflow changes are needed
- exact mechanism for search indexing or site-wide search

### 5.3 Approval gates

Do not begin schema or multi-module implementation until:

1. the public people contract is approved
2. the public scope contract is approved
3. the editorial permission model is approved
4. the image/performance budget is approved

## 6. Phase 1 — Public People Platform

Status: Implemented baseline
Code refs: `ifitwala_ed/hr/doctype/employee/*`, `ifitwala_ed/website/public_people.py`, `ifitwala_ed/website/providers/leadership.py`, `ifitwala_ed/website/providers/staff_directory.py`, `ifitwala_ed/website/renderer.py`, `ifitwala_ed/utilities/image_utils.py`
Test refs: `ifitwala_ed/website/tests/test_public_people.py`, `ifitwala_ed/website/tests/test_leadership_provider.py`, `ifitwala_ed/website/tests/test_staff_directory_provider.py`, `ifitwala_ed/website/tests/test_website_route_context.py`, `ifitwala_ed/utilities/test_employee_image_utils.py`

This is the first real product layer to build after Phase 0 approval.

### 6.1 Objective

Replace special-case staff rendering with a canonical public people platform that powers:

- leadership blocks
- faculty/staff blocks
- directory pages
- optional profile pages
- admissions and contact staff surfaces

### 6.2 Target capabilities

1. Canonical public people service layer.
   - one provider/service path for website-visible employees
   - no repeated role/school logic in each block

2. Public directory surface.
   - search/filter/grouping
   - school-aware and role-aware presentation
   - featured people support

3. Website-owned public presentation layer.
   - public intro/bio/contact/display controls
   - optional school-specific presentation when approved
   - exact schema names intentionally deferred to Phase 0 approval

4. Optional profile pages.
   - off by default
   - powered by the same public people model
   - no separate identity store

5. Reuse-first block behavior.
   - leadership block becomes a people-module consumer
   - future faculty/counselor/admin/operations blocks consume the same service

### 6.3 UX rules

- exact-school default remains the standard
- descendant inclusion is explicit per module or per selected group only
- if the surface mixes schools, the UI must label school membership
- image-heavy people listings must use governed derivatives only

## 7. Phase 2 — Core Dynamic Website Modules

Status: Implemented baseline
Code refs: `ifitwala_ed/website/providers/program_list.py`, `ifitwala_ed/website/providers/course_catalog.py`, `ifitwala_ed/website/providers/story_feed.py`, `ifitwala_ed/website/providers/academic_calendar.py`, `ifitwala_ed/website/site_notices.py`, `ifitwala_ed/website/block_registry.py`
Test refs: `ifitwala_ed/website/tests/test_program_list_provider.py`, `ifitwala_ed/website/tests/test_course_catalog_provider.py`, `ifitwala_ed/website/tests/test_story_feed_provider.py`, `ifitwala_ed/website/tests/test_academic_calendar_provider.py`, `ifitwala_ed/website/tests/test_site_notices.py`

After the people platform is stable, build the reusable modules that strong school CMS products rely on daily.

### 7.1 Recommended order

1. calendars
2. alerts / emergency banners / timed notices
3. news / stories / announcements
4. document/resource cards
5. forms / CTA modules with stronger operational reuse

### 7.2 Required platform behaviors

- reusable feeds instead of one-off page content duplication
- explicit school/organization ownership
- scheduled publishing and expiry
- editor-safe workflows
- consistent provider contracts
- no raw private file paths in display payloads

## 8. Phase 3 — Editorial Governance And Publishing Operations

Status: Implemented baseline
Code refs: `ifitwala_ed/school_site/doctype/school_website_page/*`, `ifitwala_ed/school_site/doctype/website_story/*`, `ifitwala_ed/school_site/doctype/website_notice/*`, `ifitwala_ed/school_site/doctype/program_website_profile/*`, `ifitwala_ed/school_site/doctype/course_website_profile/*`, `ifitwala_ed/website/publication.py`, `ifitwala_ed/website/permissions.py`, `ifitwala_ed/hooks.py`
Test refs: `ifitwala_ed/school_site/doctype/school_website_page/test_school_website_page.py`, `ifitwala_ed/school_site/doctype/program_website_profile/test_program_website_profile.py`, `ifitwala_ed/school_site/doctype/course_website_profile/test_course_website_profile.py`

The goal of this phase is to make the system operable by non-technical school teams.

### 8.1 Target capabilities

- scoped publisher roles by school
- stronger preview and publish workflow
- scheduled publication and expiry
- clearer page/module ownership
- safer reuse of shared content
- visibility into what is stale, unpublished, or missing required content

### 8.2 Product rule

The website should feel calm and governed for school staff.
Editors should not need to understand internal implementation details to publish high-quality pages safely.

## 9. Phase 4 — Multi-Site Governance

Status: Planned
Code refs: `ifitwala_ed/www/index.py`, `ifitwala_ed/website/utils.py`, `ifitwala_ed/website/renderer.py`, `ifitwala_ed/docs/website/05_school_slug_vs_page_route.md`
Test refs: `ifitwala_ed/website/tests/test_root_route_resolution.py`

This phase broadens the school-first platform into a multi-site platform without making district behavior the default.

### 9.1 Target capabilities

- organization hub + school site coordination
- explicit cross-site syndication
- shared theme/profile tokens
- school selector / site switcher where useful
- organization-level discovery surfaces
- optional division/campus presentation overlays

### 9.2 Guardrails

- no silent cross-school inheritance
- no sibling-school leakage
- explicit ownership and review for shared content
- independent-school customers must not pay a complexity tax for multi-school functionality

## 10. Phase 5 — Accessibility, Performance, And Website Ops

Status: Planned
Code refs: `ifitwala_ed/utilities/image_utils.py`, `ifitwala_ed/website/providers/*.py`, `ifitwala_ed/public/website/*`, `ifitwala_ed/docs/files_and_policies/files_05_organization_media_governance.md`, `ifitwala_ed/docs/high_concurrency_contract.md`
Test refs: `ifitwala_ed/utilities/test_employee_image_utils.py`, existing provider tests above; broader operational tests do not yet exist

This phase turns the website from "feature complete" into "operationally strong."

### 10.1 Target capabilities

- page performance budgets
- accessibility audits and remediation workflows
- stale content reporting
- broken link/media detection
- image-size and cache invalidation enforcement
- editor-facing quality checks before publish

### 10.2 Product rule

Accessibility and performance must be treated as ongoing platform operations, not a one-time launch milestone.

## 11. Phase 6 — Optional Personal Pages And Advanced Website Differentiators

Status: Planned, lower priority
Code refs: `None yet`
Test refs: `None`

Only after the people platform, module platform, and operations are stable should the product add optional personal-page capabilities.

### 11.1 Target capabilities

- optional personal pages for teachers or other staff
- optional class/program landing extensions where approved
- stronger site search and discovery
- advanced personalization only after governance is solid

### 11.2 Product rule

Do not force every teacher or counselor into page maintenance.
The default product value should come from strong profiles and directories first.

## 12. Recommended First Implementation Slice

Status: Planned
Code refs: `ifitwala_ed/docs/website/01_architecture_notes.md`, `ifitwala_ed/docs/website/03_website_pages_provider.md`, `ifitwala_ed/docs/website/06_block_props_guide.md`, `ifitwala_ed/docs/hr/employee.md`, `ifitwala_ed/docs/files_and_policies/files_05_organization_media_governance.md`
Test refs: `None`

The immediate next approved work should be:

1. Write the canonical public people contract.
2. Write the canonical public website scope contract for school vs descendant inclusion.
3. Write the canonical editorial governance contract for website modules.
4. Decide the schema direction for the website-owned employee presentation layer without inventing final field names prematurely.

That work is intentionally documentation-first because the current system already has enough live website behavior that schema or surface changes without contract approval would create drift.

## 13. Risks If This Sequence Is Ignored

Status: Planned
Code refs: `ifitwala_ed/website/providers/leadership.py`, `ifitwala_ed/website/block_registry.py`, `ifitwala_ed/docs/website/03_website_pages_provider.md`
Test refs: `ifitwala_ed/website/tests/test_leadership_provider.py`

If the team skips the foundation phase and keeps adding blocks directly:

- public people logic will fragment across blocks
- school-scope behavior will drift
- image and cache performance regressions will repeat
- editors will inherit inconsistent publishing behavior
- independent-school simplicity will erode under multi-school edge cases
- optional personal pages will become a second uncontrolled content system

## 14. Open Questions Requiring Future Approval

Status: Planned
Code refs: `None`
Test refs: `None`

The following decisions remain open:

1. Should the website-owned public presentation record be school-scoped, organization-scoped, or support both?
2. Which `Employee` fields are safe to expose publicly by default, and which require explicit opt-in?
3. Should scheduled publish/expiry live on `School Website Page` only, or also on reusable website-owned content modules?
4. How much search should be phase-2 baseline versus later-phase enhancement?
5. Should organization-level hubs be allowed to surface school-owned people/news/calendar items directly, or only through explicit syndication records?
