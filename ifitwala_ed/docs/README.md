# Ifitwala_Ed Documentation Map

Status: Canonical index
Code refs: None
Test refs: None
Last reset: 2026-04-19

`ifitwala_ed/docs/` is the authoritative home for architecture, runtime contracts, testing policy, and product-facing documentation.

Use this folder as a router, not as a second contract layer.

Read in this order:

1. nearest applicable `AGENTS.md`
2. this file
3. the relevant docs-folder `README.md` when one exists
4. the feature's canonical contract doc(s)

Cross-cutting contracts every agent should know:

- `high_concurrency_contract.md`
- `nested_scope_contract.md`
- `testing/01_test_strategy.md`

Canonical labeling used in the docs reset:

- `Locked target architecture` means the intended model new work must converge toward.
- `Current runtime` means what the code currently does today.
- `Transitional compatibility` means temporary bridge behavior that must not be extended.

Governed file architecture read order:

1. `files_and_policies/README.md`
2. `files_and_policies/files_01_architecture_notes.md`
   locked target architecture for governed files and media
3. `files_and_policies/files_03_implementation.md`
   current runtime, known non-conformances, and remediation order
4. `files_and_policies/files_07_education_file_semantics_and_cross_app_contract.md`
   locked cross-app workflow/spec contract

Important rule for agents:

- if current code differs from the locked target architecture, do not copy the current code pattern into new work
- use `files_03_implementation.md` as the gap register, not as permission to preserve the old design

Current domain indexes:

- `accounting/README.md`
- `admission/README.md`
- `assessment/README.md`
- `curriculum/README.md`
- `enrollment/README.md`
- `files_and_policies/README.md`
- `scheduling/README.md`
- `spa/README.md`
- `testing/README.md`
- `website/README.md`

Folder guidance:

- `docs_md/` is primarily end-user and DocType-facing documentation, not the default source for runtime architecture.
- `audit/` contains point-in-time reviews and should not be treated as canonical behavior authority.
- If a docs folder has no `README.md`, prefer files that clearly declare `Status`, `Code refs`, and `Test refs`.
