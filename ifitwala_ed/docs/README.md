# Ifitwala_Ed Documentation Map

Status: Canonical index
Code refs: None
Test refs: None

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
- If a docs folder has no `README.md`, prefer files that clearly declare `Canonical`, `Active`, `Locked`, or concrete `Status` / `Code refs` / `Test refs`.
