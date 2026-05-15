# ifitwala_ed/codex_cli.py

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_BACKEND_SMOKE_MODULES = (
    "ifitwala_ed.schedule.test_enrollment_engine",
    "ifitwala_ed.schedule.doctype.program_enrollment_request.test_program_enrollment_request",
    "ifitwala_ed.api.test_guardian_home",
    "ifitwala_ed.api.test_users",
    "ifitwala_ed.hr.test_leave_permissions",
)

DETERMINISM_CANARY_MODULE = "ifitwala_ed.tests.test_deterministic_suite"

E2E_PACK_SPECS = {
    "smoke": "cypress/e2e/{hub/staff-home.cy.js,hub/route-resolution.cy.js,admissions/profile-save.cy.js}",
    "critical": "cypress/e2e/**/*.cy.js",
}


@dataclass(frozen=True)
class CommandSpec:
    argv: tuple[str, ...]
    cwd: Path = REPO_ROOT


def _format_command(argv: Sequence[str]) -> str:
    return " ".join(shlex.quote(part) for part in argv)


def _run_command(spec: CommandSpec, dry_run: bool) -> int:
    print(f"[codex] {_format_command(spec.argv)} (cwd={spec.cwd})")
    if dry_run:
        return 0

    completed = subprocess.run(list(spec.argv), cwd=str(spec.cwd), check=False)
    return completed.returncode


def _run_specs(specs: Iterable[CommandSpec], *, dry_run: bool, fail_fast: bool) -> int:
    failures = 0
    last_rc = 0

    for spec in specs:
        rc = _run_command(spec, dry_run=dry_run)
        if rc != 0:
            failures += 1
            last_rc = rc
            if fail_fast:
                return rc

    if failures:
        print(f"[codex] completed with {failures} failing command(s).")
        return last_rc or 1

    return 0


def _lint_specs(
    *, include_pre_commit: bool, include_ruff: bool, include_contracts: bool, include_metrics: bool
) -> list[CommandSpec]:
    specs: list[CommandSpec] = []

    if include_pre_commit:
        specs.append(CommandSpec(("pre-commit", "run", "--all-files")))
    if include_ruff:
        specs.append(CommandSpec(("ruff", "check", ".")))
    if include_contracts:
        specs.append(CommandSpec(("bash", "scripts/contracts_guardrails.sh")))
    if include_metrics:
        specs.append(CommandSpec(("bash", "scripts/test_metrics.sh")))

    return specs


def _backend_smoke_specs(site: str, modules: Sequence[str]) -> list[CommandSpec]:
    return [
        CommandSpec(("bench", "--site", site, "run-tests", "--app", "ifitwala_ed", "--module", module))
        for module in modules
    ]


def _determinism_canary_specs(site: str) -> list[CommandSpec]:
    return _backend_smoke_specs(site, (DETERMINISM_CANARY_MODULE, DETERMINISM_CANARY_MODULE))


def _desk_build_specs() -> list[CommandSpec]:
    return [
        CommandSpec(("yarn", "install", "--frozen-lockfile")),
        CommandSpec(("yarn", "build")),
    ]


def _spa_typecheck_specs() -> list[CommandSpec]:
    return [
        CommandSpec(("yarn", "--cwd", "ifitwala_ed/ui-spa", "install", "--frozen-lockfile")),
        CommandSpec(("yarn", "--cwd", "ifitwala_ed/ui-spa", "type-check")),
    ]


def _e2e_prepare_specs(site: str, pack: str) -> list[CommandSpec]:
    return [
        CommandSpec(
            (
                "bench",
                "--site",
                site,
                "execute",
                "ifitwala_ed.tests.e2e.scenarios.prepare_pack",
                "--kwargs",
                json.dumps({"pack": pack, "reset_first": 1}),
            )
        )
    ]


def _e2e_run_specs(
    *,
    base_url: str,
    site: str,
    pack: str,
    open_runner: bool,
    headed: bool,
) -> list[CommandSpec]:
    normalized_pack = str(pack or "critical").strip().lower() or "critical"
    if normalized_pack not in E2E_PACK_SPECS:
        raise ValueError(f"unsupported e2e pack: {pack}")

    argv = [
        "yarn",
        "cypress",
        "open" if open_runner else "run",
        "--config",
        f"baseUrl={base_url}",
        "--env",
        f"ifitwalaSite={site},ifitwalaPack={normalized_pack}",
    ]

    spec_pattern = E2E_PACK_SPECS[normalized_pack]
    if spec_pattern:
        argv.extend(["--spec", spec_pattern])
    if headed and not open_runner:
        argv.append("--headed")

    return [CommandSpec(tuple(argv))]


def cmd_doctor(args: argparse.Namespace) -> int:
    tool_names = ("python3", "bash", "rg", "ruff", "yarn", "bench")
    missing: list[str] = []

    for tool in tool_names:
        resolved = shutil.which(tool)
        if resolved:
            print(f"[codex] ok     {tool:10} {resolved}")
        else:
            print(f"[codex] missing {tool:10}")
            missing.append(tool)

    if missing and args.strict:
        print(f"[codex] strict mode failed; missing tools: {', '.join(missing)}")
        return 1
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    specs = _lint_specs(
        include_pre_commit=args.with_pre_commit,
        include_ruff=not args.skip_ruff,
        include_contracts=not args.skip_contracts,
        include_metrics=not args.skip_metrics,
    )
    if not specs:
        print("[codex] nothing selected for lint.")
        return 0

    return _run_specs(specs, dry_run=args.dry_run, fail_fast=args.fail_fast)


def cmd_backend_smoke(args: argparse.Namespace) -> int:
    if not args.site:
        print("[codex] error: --site is required for backend-smoke.", file=sys.stderr)
        return 2

    modules = args.module or list(DEFAULT_BACKEND_SMOKE_MODULES)
    specs = _backend_smoke_specs(args.site, modules)
    return _run_specs(specs, dry_run=args.dry_run, fail_fast=args.fail_fast)


def cmd_determinism_canary(args: argparse.Namespace) -> int:
    if not args.site:
        print("[codex] error: --site is required for determinism-canary.", file=sys.stderr)
        return 2

    return _run_specs(_determinism_canary_specs(args.site), dry_run=args.dry_run, fail_fast=args.fail_fast)


def cmd_desk_build(args: argparse.Namespace) -> int:
    return _run_specs(_desk_build_specs(), dry_run=args.dry_run, fail_fast=args.fail_fast)


def cmd_spa_typecheck(args: argparse.Namespace) -> int:
    return _run_specs(_spa_typecheck_specs(), dry_run=args.dry_run, fail_fast=args.fail_fast)


def cmd_ci(args: argparse.Namespace) -> int:
    specs: list[CommandSpec] = []

    if not args.skip_lint:
        specs.extend(
            _lint_specs(
                include_pre_commit=args.with_pre_commit,
                include_ruff=True,
                include_contracts=True,
                include_metrics=True,
            )
        )

    if not args.skip_frontend:
        specs.extend(_desk_build_specs())
        specs.extend(_spa_typecheck_specs())

    if not args.skip_backend:
        if not args.site:
            print("[codex] error: --site is required for ci unless --skip-backend is set.", file=sys.stderr)
            return 2
        specs.extend(_backend_smoke_specs(args.site, args.module or list(DEFAULT_BACKEND_SMOKE_MODULES)))

    if not specs:
        print("[codex] nothing selected for ci.")
        return 0

    return _run_specs(specs, dry_run=args.dry_run, fail_fast=args.fail_fast)


def cmd_e2e(args: argparse.Namespace) -> int:
    if not args.site:
        print("[codex] error: --site is required for e2e.", file=sys.stderr)
        return 2
    if not args.base_url:
        print("[codex] error: --base-url is required for e2e.", file=sys.stderr)
        return 2

    pack = str(args.pack or "critical").strip().lower() or "critical"
    if pack not in E2E_PACK_SPECS:
        print(
            f"[codex] error: unsupported --pack '{args.pack}'. Expected one of: {', '.join(sorted(E2E_PACK_SPECS))}.",
            file=sys.stderr,
        )
        return 2

    specs: list[CommandSpec] = []
    if not args.skip_frontend_build:
        specs.extend(_desk_build_specs())
    if not args.skip_prepare:
        specs.extend(_e2e_prepare_specs(args.site, pack))
    specs.extend(
        _e2e_run_specs(
            base_url=args.base_url,
            site=args.site,
            pack=pack,
            open_runner=args.open,
            headed=args.headed,
        )
    )
    return _run_specs(specs, dry_run=args.dry_run, fail_fast=args.fail_fast)


def _add_common_command_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them.")
    parser.add_argument("--fail-fast", action="store_true", help="Stop immediately on first failing command.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex",
        description="Ifitwala developer CLI for local CI-aligned checks.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="Verify required local developer tools.")
    doctor_parser.add_argument("--strict", action="store_true", help="Return non-zero when a required tool is missing.")
    doctor_parser.set_defaults(func=cmd_doctor)

    lint_parser = subparsers.add_parser("lint", help="Run local lint and guardrail checks.")
    _add_common_command_flags(lint_parser)
    lint_parser.add_argument("--with-pre-commit", action="store_true", help="Also run pre-commit --all-files.")
    lint_parser.add_argument("--skip-ruff", action="store_true", help="Skip Ruff checks.")
    lint_parser.add_argument("--skip-contracts", action="store_true", help="Skip SPA contract guardrails.")
    lint_parser.add_argument("--skip-metrics", action="store_true", help="Skip backend test baseline metrics.")
    lint_parser.set_defaults(func=cmd_lint)

    backend_parser = subparsers.add_parser(
        "backend-smoke",
        help="Run backend smoke modules with bench run-tests.",
    )
    _add_common_command_flags(backend_parser)
    backend_parser.add_argument("--site", help="Frappe site name (required).")
    backend_parser.add_argument(
        "--module",
        action="append",
        default=[],
        help="Python module to test. Repeatable. Defaults to CI smoke modules.",
    )
    backend_parser.set_defaults(func=cmd_backend_smoke)

    canary_parser = subparsers.add_parser(
        "determinism-canary",
        help="Run the deterministic DB harness canary twice on the same site.",
    )
    _add_common_command_flags(canary_parser)
    canary_parser.add_argument("--site", help="Frappe site name (required).")
    canary_parser.set_defaults(func=cmd_determinism_canary)

    desk_parser = subparsers.add_parser("desk-build", help="Run unified Desk+SPA build.")
    _add_common_command_flags(desk_parser)
    desk_parser.set_defaults(func=cmd_desk_build)

    spa_parser = subparsers.add_parser("spa-typecheck", help="Run SPA type-check flow.")
    _add_common_command_flags(spa_parser)
    spa_parser.set_defaults(func=cmd_spa_typecheck)

    e2e_parser = subparsers.add_parser("e2e", help="Prepare deterministic browser-E2E data and run Cypress.")
    _add_common_command_flags(e2e_parser)
    e2e_parser.add_argument("--site", help="Frappe site name (required).")
    e2e_parser.add_argument("--base-url", help="Running site base URL, e.g. http://127.0.0.1:8000 (required).")
    e2e_parser.add_argument(
        "--pack",
        default="critical",
        choices=tuple(sorted(E2E_PACK_SPECS)),
        help="E2E pack to prepare and run.",
    )
    e2e_parser.add_argument("--headed", action="store_true", help="Run Cypress in headed mode.")
    e2e_parser.add_argument("--open", action="store_true", help="Open the interactive Cypress runner.")
    e2e_parser.add_argument(
        "--skip-prepare",
        action="store_true",
        help="Skip deterministic scenario preparation before running Cypress.",
    )
    e2e_parser.add_argument(
        "--skip-frontend-build",
        action="store_true",
        help="Skip the root frontend build before running Cypress.",
    )
    e2e_parser.set_defaults(func=cmd_e2e)

    ci_parser = subparsers.add_parser("ci", help="Run CI-aligned local checks.")
    _add_common_command_flags(ci_parser)
    ci_parser.add_argument("--site", help="Frappe site name for backend smoke checks.")
    ci_parser.add_argument("--skip-lint", action="store_true", help="Skip lint + guardrail phase.")
    ci_parser.add_argument("--skip-frontend", action="store_true", help="Skip desk build and SPA type-check phase.")
    ci_parser.add_argument("--skip-backend", action="store_true", help="Skip backend smoke phase.")
    ci_parser.add_argument("--with-pre-commit", action="store_true", help="Include pre-commit in lint phase.")
    ci_parser.add_argument(
        "--module",
        action="append",
        default=[],
        help="Backend smoke module override. Repeatable.",
    )
    ci_parser.set_defaults(func=cmd_ci)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
