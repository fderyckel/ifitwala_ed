# Course Choice Semantics Proposal

This proposal was implemented on 2026-03-11. The sections below now describe the live runtime contract and preserve the rationale for the cutover.

The current enrollment stack has semantic drift between:

- `Course.course_group`
- `Program Course.category`
- `Program Offering Course.elective_group`
- `Program Offering Enrollment Rule.course_group`
- `Program Enrollment Request Course.choice_rank`
- `Program Enrollment Course` historical meaning

The result is that the system currently mixes:

- catalog taxonomy
- required vs optional selection
- choice-group / basket-group logic

into overlapping field names and partially missing downstream snapshots.

Important correction after IB review:

- a single group link on `Program Course` or `Program Offering Course` is not sufficient
- a course such as ESS may be valid in more than one basket/requirement group
- the model therefore needs many-to-many basket-group membership, plus a resolved group on the request/enrollment row for auditability

## 1. Current Problem

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/course/course.json`, `ifitwala_ed/curriculum/doctype/program_course/program_course.json`, `ifitwala_ed/schedule/doctype/program_offering_course/program_offering_course.json`, `ifitwala_ed/schedule/doctype/program_offering_enrollment_rule/program_offering_enrollment_rule.json`, `ifitwala_ed/schedule/doctype/program_enrollment_request_course/program_enrollment_request_course.json`, `ifitwala_ed/schedule/doctype/program_enrollment_course/program_enrollment_course.json`
Test refs: `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`, `ifitwala_ed/schedule/doctype/program_enrollment_request/test_program_enrollment_request.py`, `ifitwala_ed/schedule/test_enrollment_engine.py`

The runtime currently uses one set of words for three different meanings:

1. `Course.course_group` is a catalog/course-taxonomy field. It also drives course colors and related metadata through `Course Group`.
2. `Program Course.category` is not acting like a generic category. It is being used as a program-side choice-group signal that later seeds the offering.
3. `Program Offering Course.elective_group` is the actual offering-side basket/choice-group signal consumed by the engine and tools, but its name incorrectly implies that the field is only about electives.

The most important downstream gaps are:

- `Program Offering Enrollment Rule.course_group` compares to offering `elective_group`, so the rule language and offering language are already misaligned.
- `Program Enrollment Request Course.choice_rank` has no group on the same row, so rank is ambiguous as soon as a request spans more than one choice family.
- `Program Enrollment Request Course` does not snapshot whether a course was required or choice-grouped at request time.
- `Program Enrollment Course` does not snapshot whether a course was required or choice-grouped at committed-enrollment time.

That last point is not cosmetic. It conflicts with the locked enrollment invariant that approved/requested truth must be transactional and not recomputed later from changed catalog or offering metadata.

## 2. Current Drift Matrix

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/course/course.json`, `ifitwala_ed/curriculum/doctype/program_course/program_course.json`, `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`, `ifitwala_ed/schedule/enrollment_engine.py`, `ifitwala_ed/schedule/enrollment_request_utils.py`, `ifitwala_ed/schedule/doctype/course_enrollment_tool/course_enrollment_tool.py`
Test refs: `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`, `ifitwala_ed/schedule/doctype/program_enrollment_request/test_program_enrollment_request.py`

| Surface | Current field | Current meaning in runtime | Drift |
| --- | --- | --- | --- |
| `Course` | `course_group` | catalog taxonomy / display grouping | correct as taxonomy, but currently shares vocabulary with basket logic |
| `Program Course` | `required` | program-level required vs optional course | acceptable |
| `Program Course` | `category` | program-side choice-group source | label is too generic and hides enrollment meaning |
| `Program Offering Course` | `required` | offering-level must-take flag enforced by engine | acceptable |
| `Program Offering Course` | `elective_group` | offering-side choice-group/basket signal | name implies optional-only semantics; reused for engine rules |
| `Program Offering Enrollment Rule` | `course_group` | rule target for `REQUIRE_GROUP_COVERAGE` | does not use same vocabulary as offering row it compares against |
| `Program Enrollment Request Course` | `choice_rank` only | applicant/student preference order | unscoped without a group field on the same row |
| `Program Enrollment Request Course` | no `required` / no group snapshot | request rows rely on live offering metadata | violates transactional snapshot intent |
| `Program Enrollment Course` | no `required` / no group snapshot | committed rows rely on live offering metadata | historical meaning can drift when offering metadata changes |

## 3. Recommended Canonical Vocabulary

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/course/course.json`, `ifitwala_ed/curriculum/doctype/program_course/program_course.json`, `ifitwala_ed/schedule/doctype/program_offering_course/program_offering_course.json`, `ifitwala_ed/schedule/doctype/program_enrollment_request_course/program_enrollment_request_course.json`, `ifitwala_ed/schedule/doctype/program_enrollment_course/program_enrollment_course.json`
Test refs: `None`

The runtime now separates three concepts explicitly.

### 3.1 Catalog Taxonomy

Keep `Course.course_group` as the course-taxonomy field.

Meaning:

- subject / catalog grouping
- display/color/reporting organization
- not the enrollment basket signal

Recommended terminology in docs and UI:

- `Course Group`
- or, where needed for clarity, `Catalog Course Group`

### 3.2 Selection Requirement

Use `required` only for the question:

> Must every student in this program/offering/request/enrollment carry this course row?

Meaning:

- binary required vs not-required
- independent from taxonomy
- independent from choice grouping

`Elective` should be treated as presentation language only, not as a field-family name.

### 3.3 Basket Group

Use one canonical term for the basket / requirement-group concept:

- recommended master name: `Basket Group`
- recommended membership tables at program/offering level rather than one link field on the course row

Meaning:

- a course may belong to zero, one, or many basket groups
- basket groups are used by coverage rules, subject-group rules, and applicant selection UX
- a selected course may later be resolved as counting toward one basket group for that request/enrollment
- the group is not the same thing as course taxonomy

## 4. Recommended Target Model

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/course/course.json`, `ifitwala_ed/curriculum/doctype/program_course/program_course.json`, `ifitwala_ed/schedule/doctype/program_offering_course/program_offering_course.json`, `ifitwala_ed/schedule/doctype/program_offering_enrollment_rule/program_offering_enrollment_rule.json`, `ifitwala_ed/schedule/doctype/program_enrollment_request_course/program_enrollment_request_course.json`, `ifitwala_ed/schedule/doctype/program_enrollment_course/program_enrollment_course.json`
Test refs: `None`

Recommended end-state:

| Surface | Canonical field(s) | Meaning |
| --- | --- | --- |
| `Course` | `course_group` | taxonomy only |
| `Program Course` | `required` + basket-group membership child rows | catalog intent for requirement and allowed basket-group memberships |
| `Program Offering Course` | `required` + basket-group membership child rows | operational offering truth for requirement and allowed basket-group memberships |
| `Program Offering Enrollment Rule` | `basket_group` | basket rule target |
| `Program Enrollment Request Course` | `required`, `applied_basket_group`, `choice_rank` | request-time snapshot of how the selected course is intended/resolved in that basket |
| `Program Enrollment Course` | `required`, `credited_basket_group` | committed enrollment snapshot of how the selected course counted in that basket |

Recommended structural interpretation:

1. `required = 1` means the row is individually mandatory.
2. basket-group membership means the row is eligible to satisfy one or more basket requirements.
3. `choice_rank` is meaningful only inside one applied basket group.
4. If a course is mandatory for everyone, use `required = 1`; basket-group membership is optional and should only be used if rules/reporting truly need it.
5. If a school must choose one course from a family, keep the individual rows `required = 0`, attach them to the relevant basket groups, and enforce the obligation through basket rules.
6. If one course can satisfy multiple groups, the request/enrollment row must record which group it was counted against.

If an institution wants both taxonomy and choice semantics on the same course, that is not a contradiction:

- taxonomy stays on `Course.course_group`
- basket semantics stay on basket-group memberships

## 5. Options

Status: Implemented
Code refs: `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`, `ifitwala_ed/schedule/enrollment_engine.py`, `ifitwala_ed/schedule/enrollment_request_utils.py`
Test refs: `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`, `ifitwala_ed/schedule/doctype/program_enrollment_request/test_program_enrollment_request.py`

### Option A: Rename-only on existing `Course Group`

Interpretation:

- keep `Course Group` as the shared master
- rename `category` / `elective_group` / rule `course_group` toward basket-group terminology
- add basket-group membership tables and resolved snapshot fields downstream

Pros:

- smaller schema footprint
- less migration work
- faster cutover

Cons:

- preserves the deeper ambiguity that the same master is both taxonomy and choice-group vocabulary
- keeps color/image/display metadata attached to an enrollment-choice concept

Blind spots:

- schools may later need choice groups such as `Humanities Elective Pool` that are not meaningful as course taxonomy

Risks:

- drift returns because staff will keep reusing one master for two different purposes

### Option B: Split taxonomy from basket grouping

Interpretation:

- keep `Course Group` for taxonomy only
- introduce a dedicated master for basket semantics, recommended name `Basket Group`
- migrate program/offering/rule/request/enrollment semantics to basket-group memberships and resolved basket-group snapshots

Pros:

- clearest long-term contract
- removes the root cause, not just the labels
- works for K-12 pathways and higher-ed elective pools without overloading taxonomy

Cons:

- bigger schema change
- requires data migration and UI cleanup across multiple doctypes

Blind spots:

- some schools may deliberately want the same names in both taxonomy and choice-group vocabularies; migration UX needs to handle that without forcing one-to-one assumptions

Risks:

- larger implementation cut with more forms, APIs, tests, and reports to update together

### Option C: Leave current schema and document it better

Interpretation:

- no structural change
- tighten docs only

Pros:

- no migration

Cons:

- preserves ambiguous naming
- does not fix request/enrollment snapshot gaps
- makes applicant and self-enrollment UX harder to build correctly

Blind spots:

- future portal work will keep inventing ad hoc interpretations of `elective`

Risks:

- continued contract drift and historically unstable reporting

Recommended option: `Option B`

Reason:

`Course Group` already has clear catalog/display semantics in the current schema. Reusing it as the permanent choice-group master will keep taxonomy and enrollment selection entangled.

The IB ESS example makes the second point equally important:

- one course can belong to more than one requirement group
- therefore the target model must support many-to-many memberships, not a single renamed link field

## 6. Proposed Cutover Plan

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/program_course/program_course.json`, `ifitwala_ed/schedule/doctype/program_offering_course/program_offering_course.json`, `ifitwala_ed/schedule/doctype/program_offering_enrollment_rule/program_offering_enrollment_rule.json`, `ifitwala_ed/schedule/doctype/program_enrollment_request_course/program_enrollment_request_course.json`, `ifitwala_ed/schedule/doctype/program_enrollment_course/program_enrollment_course.json`, `ifitwala_ed/schedule/enrollment_engine.py`, `ifitwala_ed/schedule/enrollment_request_utils.py`, `ifitwala_ed/schedule/doctype/course_enrollment_tool/course_enrollment_tool.py`
Test refs: `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`, `ifitwala_ed/schedule/doctype/program_enrollment_request/test_program_enrollment_request.py`, `ifitwala_ed/schedule/test_enrollment_engine.py`

Implemented cutover sequence:

### Phase 1: Contract freeze

- approve the canonical vocabulary:
  - taxonomy = `course_group`
  - requirement = `required`
  - basket requirement family = `basket_group`
- decide whether the repository will introduce `Basket Group` or temporarily reuse `Course Group`
 - decide whether basket groups are a dedicated doctype or a scoped variant of an existing master

### Phase 2: Schema cut

- replace `Program Course.category` with program-course basket-group membership rows
- replace `Program Offering Course.elective_group` with offering-course basket-group membership rows
- replace `Program Offering Enrollment Rule.course_group` with `basket_group`
- add `required`, `applied_basket_group`, and `choice_rank` semantics to `Program Enrollment Request Course`
- add `required` and `credited_basket_group` semantics to `Program Enrollment Course`

### Phase 3: Runtime cut

- update catalog hydration helpers to emit basket-group memberships
- update enrollment engine and rule evaluation to consume basket-group memberships
- update request validation/materialization to snapshot required/group semantics plus resolved basket-group allocation
- update course-enrollment tooling warnings and labels to use basket-group semantics
- update applicant-facing selection UX to bind `choice_rank` inside the selected basket group

### Phase 4: Validation and UX rules

- enforce `choice_rank` only when an applied basket group is present
- enforce no duplicate course rows inside the same request/enrollment snapshot
- present `Elective` only as UI language derived from `required = 0` and basket-group context where relevant
- if a course belongs to multiple basket groups, require either:
  - explicit applicant/staff selection of the applied basket group, or
  - deterministic server allocation with stored audit result

### Phase 5: Documentation and cleanup

- update canonical docs for `Course`, `Program Course`, `Program Offering`, `Program Offering Course`, `Program Enrollment Request`, `Program Enrollment`, and enrollment architecture notes
- retire old field names from docs on the same cut
- remove superseded runtime paths instead of keeping long-lived compatibility shims

## 7. Implementation Notes for Applicant / Self-Enrollment UX

Status: Planned
Code refs: `ifitwala_ed/schedule/doctype/program_enrollment_request/program_enrollment_request.py`, `ifitwala_ed/ui-spa/src/pages/admissions/ApplicantStatus.vue`, `ifitwala_ed/docs/docs_md/applicant-enrollment-plan.md`
Test refs: `None`

This cleanup is now the runtime contract for applicant-facing choice pages.

If the applicant is choosing courses from a program offering:

- required rows should be shown as locked information
- optional rows should be presented in basket-group context
- when a course belongs to multiple basket groups, the UI must let the applicant indicate which basket group the choice is intended to satisfy
- `choice_rank` should only exist within one selected basket group
- the resulting `Applicant Enrollment Plan` should carry `required`, basket-group membership, selected basket-group, and `choice_rank` semantics clearly enough to hydrate a real request later

If this cleanup is not done first, the portal will have to guess whether:

- `category`
- `elective_group`
- `course_group`

are actually the same thing. That will produce more drift, not less.

## 8. Contract Matrix

Status: Implemented
Code refs: `ifitwala_ed/curriculum/doctype/course/course.json`, `ifitwala_ed/curriculum/doctype/program_course/program_course.json`, `ifitwala_ed/schedule/doctype/program_offering_course/program_offering_course.json`, `ifitwala_ed/schedule/doctype/program_offering_enrollment_rule/program_offering_enrollment_rule.json`, `ifitwala_ed/schedule/doctype/program_enrollment_request_course/program_enrollment_request_course.json`, `ifitwala_ed/schedule/doctype/program_enrollment_course/program_enrollment_course.json`, `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`, `ifitwala_ed/schedule/enrollment_engine.py`, `ifitwala_ed/schedule/enrollment_request_utils.py`, `ifitwala_ed/schedule/doctype/course_enrollment_tool/course_enrollment_tool.py`
Test refs: `ifitwala_ed/schedule/doctype/program_offering/test_program_offering.py`, `ifitwala_ed/schedule/doctype/program_enrollment_request/test_program_enrollment_request.py`, `ifitwala_ed/schedule/test_enrollment_engine.py`

| Area | Current owner | Implemented owner | State |
| --- | --- | --- | --- |
| Catalog taxonomy | `Course.course_group` | unchanged | Implemented |
| Program basket-group source | `Program Course.category` | basket-group membership rows | Implemented |
| Offering basket-group source | `Program Offering Course.elective_group` | basket-group membership rows | Implemented |
| Basket rule target | `Program Offering Enrollment Rule.course_group` | `Program Offering Enrollment Rule.basket_group` | Implemented |
| Request-row snapshot | none | `Program Enrollment Request Course.required`, `applied_basket_group`, `choice_rank` | Implemented |
| Committed-row snapshot | none | `Program Enrollment Course.required`, `credited_basket_group` | Implemented |
| Engine basket coverage | single offering `elective_group` | basket-group membership + resolved allocation | Implemented |
| Applicant/self-enrollment UI | ambiguous group semantics | basket-group aware selection + scoped `choice_rank` | Planned |

## 9. Final Recommendation

Status: Implemented
Code refs: `ifitwala_ed/schedule/enrollment_engine.py`, `ifitwala_ed/schedule/enrollment_request_utils.py`, `ifitwala_ed/schedule/doctype/program_offering/program_offering.py`
Test refs: `None`

The semantic cleanup is now the required foundation before building more applicant course-choice UX.

Implemented decision:

1. Keep `Course.course_group` as taxonomy only.
2. Stop using `elective` as the data-model term for grouping.
3. Standardize program/offering/rule/request/enrollment basket semantics on basket-group memberships, not a single group link field.
4. Snapshot `required` plus resolved basket-group meaning into request and enrollment child rows.
5. Prefer a dedicated `Basket Group` master rather than permanently reusing `Course Group` for two meanings.

That is the cleanest fix because it removes the current ambiguity at the exact layers where admissions choice UX, enrollment validation, and committed academic history need the contract to be stable.
