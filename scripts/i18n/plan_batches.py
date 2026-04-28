#!/usr/bin/env python3
"""Summarize i18n audit findings into reviewable cleanup batches."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = REPO_ROOT / ".i18n-audit" / "current.json"


def load_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Audit report not found: {path}\nRun: python3 scripts/i18n/audit.py")
    return json.loads(path.read_text(encoding="utf-8"))


def module_for(path: str) -> str:
    parts = path.split("/")
    if parts and parts[0] == "ifitwala_ed" and len(parts) > 1:
        return parts[1]
    return parts[0] if parts else "unknown"


def matches_filters(finding: dict[str, Any], args: argparse.Namespace) -> bool:
    if args.severity and finding.get("severity") not in args.severity:
        return False
    if args.bucket and finding.get("bucket") not in args.bucket:
        return False
    if args.surface and finding.get("surface") not in args.surface:
        return False
    if args.kind and finding.get("kind") not in args.kind:
        return False
    return True


def summarize_file(findings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "count": len(findings),
        "buckets": dict(sorted(Counter(item.get("bucket", "") for item in findings).items())),
        "kinds": dict(sorted(Counter(item.get("kind", "") for item in findings).items())),
        "surfaces": dict(sorted(Counter(item.get("surface", "") for item in findings).items())),
        "first_line": min(int(item.get("line") or 1) for item in findings),
    }


def build_batches(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_module: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for finding in findings:
        path = str(finding.get("path") or "")
        by_module[module_for(path)][path].append(finding)

    batches: list[dict[str, Any]] = []
    for module, files in by_module.items():
        file_rows = [{"path": path, **summarize_file(file_findings)} for path, file_findings in sorted(files.items())]
        bucket_counts = Counter()
        kind_counts = Counter()
        surface_counts = Counter()
        for row in file_rows:
            bucket_counts.update(row["buckets"])
            kind_counts.update(row["kinds"])
            surface_counts.update(row["surfaces"])
        batches.append(
            {
                "module": module,
                "count": sum(row["count"] for row in file_rows),
                "files": len(file_rows),
                "buckets": dict(sorted(bucket_counts.items())),
                "kinds": dict(sorted(kind_counts.items())),
                "surfaces": dict(sorted(surface_counts.items())),
                "file_rows": sorted(file_rows, key=lambda row: (-row["count"], row["path"])),
            }
        )
    return sorted(batches, key=lambda row: (-row["count"], row["module"]))


def print_batches(batches: list[dict[str, Any]], args: argparse.Namespace) -> None:
    if not batches:
        print("i18n batch planner: no findings match the filters")
        return

    total = sum(batch["count"] for batch in batches)
    print(f"i18n batch planner: {total} findings across {len(batches)} module(s)")
    print()

    for batch in batches[: args.limit]:
        print(f"{batch['module']}: {batch['count']} finding(s), {batch['files']} file(s)")
        print(f"  buckets: {format_counts(batch['buckets'])}")
        print(f"  kinds: {format_counts(batch['kinds'])}")
        for row in batch["file_rows"][: args.files_per_module]:
            print(f"  - {row['path']}:{row['first_line']} ({row['count']}; {format_counts(row['buckets'])})")
        if len(batch["file_rows"]) > args.files_per_module:
            remaining = len(batch["file_rows"]) - args.files_per_module
            print(f"  - ... {remaining} more file(s)")
        print()


def format_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{key}={value}" for key, value in counts.items()) or "none"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help="Audit JSON report path. Defaults to .i18n-audit/current.json.",
    )
    parser.add_argument(
        "--severity",
        action="append",
        default=["warning"],
        help="Finding severity to include. Repeatable. Defaults to warning.",
    )
    parser.add_argument("--bucket", action="append", help="Finding bucket to include. Repeatable.")
    parser.add_argument("--surface", action="append", help="Finding surface to include. Repeatable.")
    parser.add_argument("--kind", action="append", help="Finding kind to include. Repeatable.")
    parser.add_argument("--limit", type=int, default=12, help="Maximum module batches to print.")
    parser.add_argument(
        "--files-per-module",
        type=int,
        default=8,
        help="Maximum files to print per module batch.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path = args.report if args.report.is_absolute() else REPO_ROOT / args.report
    report = load_report(report_path)
    findings = [item for item in report.get("findings", []) if matches_filters(item, args)]
    batches = build_batches(findings)

    if args.json:
        print(json.dumps({"count": len(findings), "batches": batches}, indent=2, sort_keys=True))
    else:
        print_batches(batches, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
