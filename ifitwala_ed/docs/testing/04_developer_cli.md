<!-- ifitwala_ed/docs/testing/04_developer_cli.md -->
# Ifitwala_Ed Developer CLI (`codex`)

## 1. Purpose

Provide one repo-focused command surface for local developer workflows while staying aligned with existing CI contracts.

## 2. Entry Point

Run from repository root:

```bash
./scripts/codex <command> [options]
```

The wrapper invokes `python3 -m ifitwala_ed.codex_cli`.

## 3. Commands

1. `doctor`
- Checks local tool availability (`python3`, `bash`, `rg`, `ruff`, `yarn`, `bench`).

2. `lint`
- Runs repo guardrails:
  - `ruff check .`
  - `bash scripts/contracts_guardrails.sh`
  - `bash scripts/test_metrics.sh`
- Optional: `--with-pre-commit` adds `pre-commit run --all-files`.

3. `backend-smoke --site <site>`
- Runs the default backend smoke modules (same baseline as CI), or custom modules with repeated `--module`.
- Local bench/site should run on **Frappe v16** to stay CI-compatible.

4. `desk-build`
- Runs `yarn install --frozen-lockfile` then `yarn build`.

5. `spa-typecheck`
- Runs SPA dependency install and `yarn type-check` in `ifitwala_ed/ui-spa`.

6. `ci --site <site>`
- CI-aligned composite command:
  - lint phase
  - frontend phase (`desk-build` + `spa-typecheck`)
  - backend smoke phase
- Phases can be skipped with `--skip-lint`, `--skip-frontend`, `--skip-backend`.

7. `e2e --site <site> --base-url <url>`
- Prepares deterministic browser-test scenarios through `ifitwala_ed.tests.e2e.scenarios.prepare_pack`.
- Runs the repo-root Cypress suite against the running site.
- Supported packs:
  - `smoke`
  - `critical`
- Useful flags:
  - `--pack smoke`
  - `--headed`
  - `--open`
  - `--skip-prepare`
  - `--skip-frontend-build`

Root package scripts mirror the CLI and expect `SITE` and `BASE_URL` env vars:
- `yarn test:e2e:smoke`
- `yarn test:e2e:critical`
- `yarn test:e2e:headed`
- `yarn test:e2e:open`

## 4. Execution Controls

1. `--dry-run`
- Prints commands without execution.

2. `--fail-fast`
- Stops at first failing command.

Without `--fail-fast`, command groups continue and report failures at the end.
