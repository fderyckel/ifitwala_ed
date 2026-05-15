<!-- ifitwala_ed/docs/website/10_public_people_contract_proposal.md -->
# Public People Contract Proposal

This note is a non-authoritative proposal.

Implemented runtime contract now lives in:

- `ifitwala_ed/docs/website/10_public_people_contract.md`

Current canonical runtime remains defined by:

- `ifitwala_ed/docs/website/01_architecture_notes.md`
- `ifitwala_ed/docs/website/03_website_pages_provider.md`
- `ifitwala_ed/docs/website/06_block_props_guide.md`
- `ifitwala_ed/docs/hr/employee.md`
- `ifitwala_ed/docs/files_and_policies/files_05_organization_media_governance.md`

This proposal exists to define the target public people model before additional schema changes, new directory/profile surfaces, or cross-module public staff behavior changes are approved.

## 1. Decision Goal

Status: Planned
Code refs: `ifitwala_ed/hr/doctype/employee/*`, `ifitwala_ed/website/providers/leadership.py`, `ifitwala_ed/website/blocks/leadership.html`, `ifitwala_ed/utilities/image_utils.py`, `ifitwala_ed/website/block_registry.py`, `ifitwala_ed/public/js/website_props_builder.js`
Test refs: `ifitwala_ed/website/tests/test_leadership_provider.py`, `ifitwala_ed/utilities/test_employee_image_utils.py`, `ifitwala_ed/school_site/doctype/school_website_page/test_school_website_page.py`

Target runtime outcome:

1. Ifitwala_Ed has one canonical public people model for school websites.
2. `Employee` remains the public staff source of truth.
3. The current implementation stays `Employee`-first. Any future public presentation fields should be justified explicitly and should not replace `Employee` as the source of truth.
4. Public people rendering supports leadership, teachers, counselors, operational staff, and other school-visible employee groups through one shared contract.
5. Public directory pages, leadership blocks, and optional personal pages all consume the same underlying people service.
6. Exact-school scope remains the public default, with explicit and bounded descendant inclusion only where the module contract allows it.
7. Public people surfaces use governed derivatives, accessibility-safe output, and clear cache invalidation ownership.

The product goal is simple:

`one employee truth -> one public people contract -> many reusable school website surfaces`

## 2. Why This Model Fits Top-Tier School CMS Patterns

Status: Planned
Code refs: `None`
Test refs: `None`

This proposal is anchored in recurring patterns from official vendor materials for Finalsite, SchoolStatus, and Blackbaud.

### 2.1 What those platforms consistently emphasize

1. Directories are a core module, not a custom page.
   - Finalsite markets public/private directories, search/filter tools, and page-by-page control through its directory tooling.
   - Blackbaud positions directories, notifications, and calendars as built-in platform features.

2. Content should be maintained once and reused everywhere.
   - Finalsite repeatedly frames this as create-once-publish-everywhere behavior across directories, calendars, alerts, and portals.

3. Teacher pages are optional extensions, not the minimum viable people experience.
   - Finalsite offers teacher pages as a module.
   - SchoolStatus explicitly warns against forcing every teacher to maintain a site and recommends at least having a strong faculty directory.

4. Accessibility is part of ongoing operations.
   - SchoolStatus exposes an accessibility dashboard and service plan with ongoing scans.
   - Finalsite and Blackbaud both position accessibility as a built-in platform concern rather than a one-time migration task.

5. Multi-site consistency matters, but school identity still matters.
   - SchoolStatus markets districtwide plus individual school websites with cohesive branding.
   - Finalsite and Blackbaud both support multi-site or multiple-initiative experiences without implying that every school page should silently flatten all subordinate content.

### 2.2 Product implications for Ifitwala_Ed

The practical interpretation for Ifitwala_Ed is:

- build a directory/profile platform first
- keep one public source of truth for staff identity
- allow optional personal pages later
- keep school-first public scope by default
- make reuse, accessibility, and derivative media part of the contract, not best-effort extras

## 3. Product Position For Ifitwala_Ed

Status: Planned
Code refs: `ifitwala_ed/docs/website/09_website_platform_phase_proposal.md`, `ifitwala_ed/docs/setup/school_organization_scope_contract.md`, `ifitwala_ed/docs/nested_scope_contract.md`
Test refs: `ifitwala_ed/utilities/test_school_tree.py`, `ifitwala_ed/website/tests/test_leadership_provider.py`

This proposal adopts the following product posture:

### 3.1 Default customer posture

- independent-school-first
- exact-school public scope by default
- multi-school and division behavior layered on explicitly

### 3.2 Public people posture

- `Employee` owns identity truth
- current implementation reads public people directly from `Employee`
- the website must not duplicate HR identity management

### 3.3 Optionality posture

- leadership-only pages are supported
- teacher/counselor/operations/faculty directories are supported
- individual personal pages are optional
- the product must work well even when no personal pages exist

## 4. Proposed Public People Architecture

Status: Planned
Code refs: `ifitwala_ed/hr/doctype/employee/*`, `ifitwala_ed/website/providers/leadership.py`, `ifitwala_ed/utilities/image_utils.py`
Test refs: `ifitwala_ed/website/tests/test_leadership_provider.py`, `ifitwala_ed/utilities/test_employee_image_utils.py`

### 4.1 Identity truth

`Employee` remains authoritative for:

- employee identity
- school
- organization
- designation
- visibility anchor (`show_on_website`)
- governed image anchor (`employee_image`)

### 4.2 Current posture on presentation fields

The current approved direction is to keep public people data on `Employee` unless and until a future product need proves otherwise.

If additional public website fields become necessary later, they should be evaluated as `Employee` fields first, with explicit ownership and workflow reasoning.

### 4.3 Service ownership

All public people surfaces should read through one canonical website-owned people service/provider layer.

That layer should own:

- scope resolution
- public visibility filtering
- directory grouping
- role/designation resolution
- profile-card payload shape
- derivative image payload shape

This logic must not be reimplemented block by block.

## 5. Proposed Scope Contract

Status: Planned
Code refs: `ifitwala_ed/website/providers/leadership.py`, `ifitwala_ed/utilities/school_tree.py`, `ifitwala_ed/docs/setup/school_organization_scope_contract.md`, `ifitwala_ed/docs/nested_scope_contract.md`
Test refs: `ifitwala_ed/utilities/test_school_tree.py`, `ifitwala_ed/website/tests/test_leadership_provider.py`

### 5.1 Default rule

Public people scope on a school website is:

- exact current school by default

### 5.2 Allowed widening

Descendant inclusion is allowed only when:

- the specific module contract permits it
- the page author or module configuration opts in explicitly
- the result remains bounded by a declared depth rule when partial descent is intended

### 5.3 Required behavior when widened

If a public people surface includes descendant schools:

- school ownership must be visible in the UI
- sibling-school leakage must remain impossible
- the same widening rule must be reflected in provider logic, cache keys, and tests

### 5.4 Recommended scope modes

For public people modules, the target scope vocabulary should remain small:

- `current`
- `current_and_descendants`

Depth should remain explicit when needed:

- `descendant_depth = 1` for self + direct children
- omitted depth for full subtree where approved

## 6. Proposed Surface Model

Status: Planned
Code refs: `ifitwala_ed/website/providers/leadership.py`, `ifitwala_ed/website/block_registry.py`, `ifitwala_ed/website/blocks/leadership.html`
Test refs: `ifitwala_ed/website/tests/test_leadership_provider.py`

The public people platform should support the following surfaces:

### 6.1 Leadership block

- curated subset
- often role/designation-driven
- exact-school by default
- supports explicit descendant inclusion for selected roles when approved

### 6.2 Faculty & staff directory

- canonical public people surface
- searchable and filterable
- likely the default people destination for most schools
- should work well without personal pages

### 6.3 Profile page

- optional extension
- enabled only for selected employees
- must reuse the same public people payload model as the directory

### 6.4 Reusable contact/staff pickers for other public pages

- admissions contact cards
- department/staff spotlight cards
- operational contact surfaces

All of these should consume the same public people contract.

## 7. Field Ownership Proposal

Status: Planned
Code refs: `ifitwala_ed/hr/doctype/employee/*`, `ifitwala_ed/docs/hr/employee.md`
Test refs: `None`

### 7.1 Employee-owned public truth candidates

These fields are good candidates to remain directly `Employee`-owned:

- school
- organization
- designation
- show-on-website anchor
- canonical image anchor
- employee full name unless overridden for presentation

### 7.2 Future Employee field candidates

If future public website requirements justify more fields, they should be evaluated on `Employee` first:

- public headline / title override
- short marketing intro
- longer public bio
- custom ordering / featured placement
- optional public links
- optional personal-page slug and enablement

### 7.3 Explicit non-goals

The website layer must not own:

- employment status truth
- school assignment truth
- organization assignment truth
- designation identity truth
- permissions that belong to Desk/portal HR flows

## 8. Public/Private Data Boundary Proposal

Status: Planned
Code refs: `ifitwala_ed/docs/hr/employee.md`, `ifitwala_ed/docs/files_and_policies/files_05_organization_media_governance.md`
Test refs: `None`

Inspired by Finalsite's public/private directory model, Ifitwala_Ed should explicitly distinguish:

- public directory fields
- private authenticated fields
- never-public fields

This proposal recommends:

1. Public website pages expose only an approved public field set.
2. Private or staff-only contact detail is not leaked through public provider payloads.
3. If future authenticated portals reuse the same people service, they should do so through a separate authenticated contract rather than weakening the public one.

## 9. Personal Page Proposal

Status: Planned
Code refs: `None yet`
Test refs: `None`

This proposal follows the SchoolStatus recommendation pattern more closely than the "everyone gets a page" pattern.

Recommended rule:

- no employee gets a personal page by default
- the faculty/staff directory is the baseline public people experience
- personal pages are opt-in for employees or schools that actually want them

Rationale:

- better content freshness
- less editorial burden
- lower accessibility risk
- simpler school-wide consistency

Where personal pages are enabled:

- they must remain on-brand
- they must consume the same people model
- they must not introduce a second unmanaged publishing system

## 10. Accessibility And Performance Proposal

Status: Planned
Code refs: `ifitwala_ed/utilities/image_utils.py`, `ifitwala_ed/website/blocks/leadership.html`, `ifitwala_ed/templates/includes/smart_image_macro.html`, `ifitwala_ed/docs/high_concurrency_contract.md`
Test refs: `ifitwala_ed/utilities/test_employee_image_utils.py`

Anchored in the vendor patterns above, public people surfaces should treat accessibility and performance as core behavior.

### 10.1 Accessibility expectations

- semantic headings and list structure
- meaningful alt text
- labeled links and buttons
- no inaccessible image-only staff navigation
- strong defaults for profile cards and profile pages

### 10.2 Performance expectations

- derivative-first image loading
- responsive `srcset` on people cards
- bounded query counts
- cache keys include relevant scope and filter inputs
- explicit cache invalidation ownership on employee/designation/school changes

### 10.3 Document rule

If a people surface links files or downloadable profile documents in the future, it must follow governed file/display URL rules rather than guessing file paths.

## 11. Editorial Workflow Proposal

Status: Planned
Code refs: `ifitwala_ed/school_site/doctype/school_website_page/*`, `ifitwala_ed/docs/website/01_architecture_notes.md`
Test refs: `ifitwala_ed/school_site/doctype/school_website_page/test_school_website_page.py`

The public people platform should support non-technical school teams.

Recommended expectations:

- website managers can curate directories and spotlights without weakening `Employee` as the source of truth
- review/publish states remain clear
- public profile changes should be previewable
- schools with multiple editors should have clear ownership boundaries

## 12. Proposed Phase Sequence

Status: Planned
Code refs: `ifitwala_ed/docs/website/09_website_platform_phase_proposal.md`
Test refs: `None`

### Phase 0

- approve this public people contract direction
- approve exact public field boundaries
- approve the scope rules
- approve the personal-page posture

### Phase 1

- create one canonical people provider/service
- refactor leadership block to consume the shared people service
- keep the first implementation `Employee`-first

### Phase 2

- build the public faculty/staff directory
- add search, filters, grouping, and featured handling

### Phase 3

- add optional profile pages
- add school- or organization-level syndication rules where approved
- decide whether additional public presentation fields are needed on `Employee`

## 13. Risks If We Skip This Contract

Status: Planned
Code refs: `ifitwala_ed/website/providers/leadership.py`, `ifitwala_ed/website/block_registry.py`
Test refs: `ifitwala_ed/website/tests/test_leadership_provider.py`

If the team keeps building public staff surfaces without a canonical people contract:

- leadership logic will keep being duplicated
- teacher/counselor/admin/operations display rules will diverge
- public/private field exposure will become inconsistent
- scope logic will drift across blocks
- personal pages will risk becoming a second unmanaged CMS
- image and cache regressions will keep recurring

## 14. Open Questions Requiring Approval

Status: Planned
Code refs: `None`
Test refs: `None`

1. Which `Employee` contact fields, if any, are publicly safe by default?
2. Should public people search be school-local only at first, or support explicit organization-level hub search?
3. Should personal pages support posts/updates in phase one, or only static profile content initially?
4. What is the exact schema and workflow boundary between HR-managed changes and website-manager-managed public presentation edits on `Employee`?

## 15. Market Reference Links

Status: Informational
Code refs: `None`
Test refs: `None`

Official materials reviewed for this proposal:

- [Finalsite CMS for Schools](https://www.finalsite.com/school-websites/cms-for-schools)
- [Finalsite Directories](https://www.finalsite.com/school-websites/cms-for-schools/directories)
- [Finalsite Teacher Pages](https://www.finalsite.com/school-websites/cms-for-schools/online-publishing/teacher-pages)
- [Finalsite Website Notifications](https://www.finalsite.com/school-websites/cms-for-schools/website-notifications)
- [Finalsite File & Media Storage](https://www.finalsite.com/school-websites/cms-for-schools/file-management)
- [SchoolStatus Sites](https://www.schoolstatus.com/products/sites)
- [SchoolStatus recommendation on personal sites and faculty directories](https://help.sites.schoolstatus.com/hc/en-us/articles/26542264828052-What-are-SchoolStatus-Sites-recommendations-on-personal-sites-and-ADA-compliance)
- [SchoolStatus Accessibility Dashboard](https://help.sites.schoolstatus.com/hc/en-us/articles/26542594702740-Accessibility-Dashboard)
- [SchoolStatus ADA service plan FAQ](https://help.sites.schoolstatus.com/hc/en-us/articles/26542679352340-SchoolStatus-Sites-ADA-Service-Plan-FAQ-s)
- [Blackbaud School Website System](https://www.blackbaud.com/products/school-website-cms)
