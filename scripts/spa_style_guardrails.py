#!/usr/bin/env python3
"""
Guardrails for SPA style drift.

This script does two things:
1. Blocks new undefined semantic color utilities and undefined CSS variables.
2. Reports current drift indicators so cleanup can happen in controlled batches.

Current legacy debt is tracked in scripts/spa_style_guardrails_baseline.json.
That debt is allowed temporarily, but it must not grow silently.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SPA_ROOT = REPO_ROOT / "ifitwala_ed" / "ui-spa"
SRC_ROOT = SPA_ROOT / "src"
BASELINE_PATH = REPO_ROOT / "scripts" / "spa_style_guardrails_baseline.json"

SOURCE_SUFFIXES = {".vue", ".ts", ".js", ".css"}
PAGE_STYLE_VISUAL_TOKENS = (
    "background",
    "color:",
    "box-shadow",
    "border-color",
    "font-size",
    "linear-gradient",
    "radial-gradient",
)

RAW_PALETTE_RE = re.compile(
    r"\b(?:bg|text|border|ring|from|via|to)-"
    r"(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|"
    r"teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)(?:-|/|\b)"
)
SCOPED_STYLE_RE = re.compile(r"<style\s+scoped[^>]*>(.*?)</style>", re.S)
SCRIPT_BLOCK_RE = re.compile(r"<script(?:\s[^>]*)?>(.*?)</script>", re.S)
STATIC_CLASS_ATTR_RE = re.compile(r"(?<![:\w-])class\s*=\s*([\"'])(.*?)\1", re.S)
DYNAMIC_CLASS_ATTR_RE = re.compile(r"(?:v-bind:class|:class)\s*=\s*([\"'])(.*?)\1", re.S)
STRING_LITERAL_RE = re.compile(r"([\"'`])((?:\\.|(?!\1).)*)\1", re.S)
VAR_DEF_RE = re.compile(r"--([a-z0-9-]+)['\"]?\s*:")
VAR_USAGE_RE = re.compile(r"var\(\s*(--[a-z0-9-]+)\b")

SEMANTIC_COLOR_NAMES = {
    "border",
    "canopy",
    "clay",
    "flame",
    "ink",
    "jacaranda",
    "leaf",
    "line-soft",
    "moss",
    "sand",
    "sky",
    "slate-token",
    "surface",
    "surface-glass",
    "surface-soft",
    "surface-strong",
}
NATIVE_COLOR_FAMILIES = {
    "amber",
    "black",
    "blue",
    "current",
    "cyan",
    "emerald",
    "fuchsia",
    "gray",
    "green",
    "indigo",
    "inherit",
    "lime",
    "neutral",
    "orange",
    "pink",
    "purple",
    "red",
    "rose",
    "sky",
    "slate",
    "stone",
    "teal",
    "transparent",
    "violet",
    "white",
    "yellow",
    "zinc",
}
NON_COLOR_TOKENS = {
    "bg": {
        "auto",
        "bottom",
        "center",
        "contain",
        "cover",
        "fixed",
        "left",
        "local",
        "none",
        "no-repeat",
        "repeat",
        "repeat-x",
        "repeat-y",
        "right",
        "scroll",
        "top",
    },
    "text": {
        "balance",
        "base",
        "center",
        "clip",
        "ellipsis",
        "end",
        "justify",
        "left",
        "lg",
        "nowrap",
        "pretty",
        "right",
        "sm",
        "start",
        "wrap",
        "xl",
        "xs",
    },
    "border": {
        "collapse",
        "dashed",
        "dotted",
        "double",
        "hidden",
        "none",
        "separate",
        "solid",
    },
    "ring": {
        "inset",
        "offset",
    },
}


def repo_rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for path in SRC_ROOT.rglob("*"):
        if path.suffix not in SOURCE_SUFFIXES or not path.is_file():
            continue
        rel_parts = path.relative_to(SRC_ROOT).parts
        if "__tests__" in rel_parts:
            continue
        if any(marker in path.name for marker in (".test.", ".spec.")):
            continue
        files.append(path)
    return files


def load_baseline() -> dict[str, dict[str, list[str]]]:
    if not BASELINE_PATH.exists():
        return {"unknown_css_vars": {}, "unknown_semantic_colors": {}}
    return json.loads(BASELINE_PATH.read_text())


def collect_declared_vars(files: list[Path]) -> set[str]:
    declared: set[str] = set()
    for path in files:
        text = path.read_text()
        for match in VAR_DEF_RE.finditer(text):
            declared.add(f"--{match.group(1)}")
    return declared


def collect_unknown_css_vars(files: list[Path], declared_vars: set[str]) -> dict[str, set[str]]:
    unknown: dict[str, set[str]] = defaultdict(set)
    for path in files:
        text = path.read_text()
        rel = repo_rel(path)
        for match in VAR_USAGE_RE.finditer(text):
            var_name = match.group(1)
            if var_name not in declared_vars:
                unknown[var_name].add(rel)
    return unknown


def is_non_color_token(prefix: str, token: str) -> bool:
    if prefix == "bg":
        if token.startswith(("gradient-to-", "clip-", "origin-", "opacity-", "blend-")):
            return True
    if prefix == "text":
        if re.fullmatch(r"[2-9]xl", token):
            return True
    if prefix == "border":
        if re.fullmatch(r"\d+", token):
            return True
        if re.fullmatch(r"[tblrxyse](?:-\d+)?", token):
            return True
    if prefix == "ring":
        if token.startswith(("offset-", "opacity-")):
            return True
        if re.fullmatch(r"\d+", token):
            return True
    return token in NON_COLOR_TOKENS.get(prefix, set())


def normalize_color_token(prefix: str, token: str) -> str | None:
    if prefix == "border":
        direction_match = re.fullmatch(r"([tblrxyse])-(.+)", token)
        if direction_match:
            remainder = direction_match.group(2)
            if re.fullmatch(r"\d+", remainder):
                return None
            return remainder
    return token


def is_allowed_color_name(token: str) -> bool:
    if token in SEMANTIC_COLOR_NAMES:
        return True
    first = token.split("-", 1)[0]
    return first in NATIVE_COLOR_FAMILIES


def strip_style_blocks(text: str) -> str:
    return re.sub(r"<style(?:\s[^>]*)?>.*?</style>", "", text, flags=re.S)


def strip_script_blocks(text: str) -> str:
    return re.sub(r"<script(?:\s[^>]*)?>.*?</script>", "", text, flags=re.S)


def sanitize_class_token(raw_token: str) -> str:
    token = raw_token.strip().strip(",;(){}[]")
    token = token.strip("'\"`<>")
    if token.startswith("!"):
        token = token[1:]
    return token


def iter_candidate_class_fragments(text: str) -> list[str]:
    fragments: list[str] = []

    markup = strip_script_blocks(strip_style_blocks(text))
    fragments.extend(match.group(2) for match in STATIC_CLASS_ATTR_RE.finditer(markup))
    for match in DYNAMIC_CLASS_ATTR_RE.finditer(markup):
        expression = match.group(2)
        fragments.extend(string_match.group(2) for string_match in STRING_LITERAL_RE.finditer(expression))

    for script_match in SCRIPT_BLOCK_RE.finditer(text):
        script = script_match.group(1)
        for string_match in STRING_LITERAL_RE.finditer(script):
            content = string_match.group(2)
            if any(marker in content for marker in ("bg-", "text-", "border-", "ring-", "from-", "via-", "to-")):
                fragments.append(content)

    return fragments


def iter_class_tokens(fragment: str) -> list[str]:
    tokens: list[str] = []
    for raw_token in fragment.split():
        token = sanitize_class_token(raw_token)
        if not token or any(char in token for char in "<=>"):
            continue
        tokens.append(token)
    return tokens


def collect_unknown_semantic_colors(files: list[Path]) -> dict[str, set[str]]:
    unknown: dict[str, set[str]] = defaultdict(set)
    for path in files:
        if path.suffix != ".vue":
            continue
        text = path.read_text()
        rel = repo_rel(path)
        for fragment in iter_candidate_class_fragments(text):
            for token in iter_class_tokens(fragment):
                class_token = token.rsplit(":", 1)[-1]
                matched_prefix = None
                for prefix in ("bg", "text", "border", "ring", "from", "via", "to"):
                    marker = f"{prefix}-"
                    if class_token.startswith(marker):
                        matched_prefix = prefix
                        token_value = class_token[len(marker) :]
                        break
                if not matched_prefix:
                    continue
                if not token_value or "[" in token_value:
                    continue
                color_name = token_value.split("/", 1)[0]
                color_name = normalize_color_token(matched_prefix, color_name)
                if not color_name:
                    continue
                if is_non_color_token(matched_prefix, color_name):
                    continue
                if is_allowed_color_name(color_name):
                    continue
                unknown[color_name].add(rel)
    return unknown


def collect_report_only_warnings(page_files: list[Path]) -> dict[str, list[str]]:
    warnings: dict[str, list[str]] = {}

    raw_palette_pages = [repo_rel(path) for path in page_files if RAW_PALETTE_RE.search(path.read_text())]
    if raw_palette_pages:
        warnings["pages_using_raw_palette_utilities"] = raw_palette_pages

    visual_scoped_pages: list[str] = []
    for path in page_files:
        text = path.read_text()
        for match in SCOPED_STYLE_RE.finditer(text):
            block = match.group(1)
            if any(token in block for token in PAGE_STYLE_VISUAL_TOKENS):
                visual_scoped_pages.append(repo_rel(path))
                break
    if visual_scoped_pages:
        warnings["pages_with_visual_scoped_css"] = visual_scoped_pages

    return warnings


def diff_from_baseline(current: dict[str, set[str]], baseline: dict[str, list[str]]) -> dict[str, set[str]]:
    diff: dict[str, set[str]] = {}
    for key, files in current.items():
        baseline_files = set(baseline.get(key, []))
        new_files = set(files) - baseline_files
        if new_files:
            diff[key] = new_files
    return diff


def print_group(title: str, findings: dict[str, set[str]] | dict[str, list[str]]) -> None:
    if not findings:
        return
    print(title)
    for key in sorted(findings):
        print(f"  {key}")
        for rel in sorted(findings[key]):
            print(f"    - {rel}")


def print_warning_summary(title: str, items: list[str], max_examples: int = 12) -> None:
    if not items:
        return
    print(f"{title}: {len(items)}")
    for rel in items[:max_examples]:
        print(f"  - {rel}")
    if len(items) > max_examples:
        print(f"  - ... {len(items) - max_examples} more")


def main() -> int:
    source_files = iter_source_files()
    page_files = [
        path for path in source_files if "/src/pages/" in path.as_posix() and "/components/" not in path.as_posix()
    ]
    baseline = load_baseline()

    declared_vars = collect_declared_vars(source_files)
    current_unknown_vars = collect_unknown_css_vars(source_files, declared_vars)
    current_unknown_colors = collect_unknown_semantic_colors(source_files)

    new_unknown_vars = diff_from_baseline(current_unknown_vars, baseline.get("unknown_css_vars", {}))
    new_unknown_colors = diff_from_baseline(current_unknown_colors, baseline.get("unknown_semantic_colors", {}))

    legacy_unknown_vars = {
        key: current_unknown_vars[key] for key in current_unknown_vars if key in baseline.get("unknown_css_vars", {})
    }
    legacy_unknown_colors = {
        key: current_unknown_colors[key]
        for key in current_unknown_colors
        if key in baseline.get("unknown_semantic_colors", {})
    }
    warnings = collect_report_only_warnings(page_files)

    print("spa style guardrails")
    print(f"source root: {SRC_ROOT}")
    print(f"baseline: {BASELINE_PATH}")

    if legacy_unknown_vars or legacy_unknown_colors:
        print()
        print("WARN: existing baseline style debt remains in the repo. Do not expand it.")
        print_group("  unknown CSS vars", legacy_unknown_vars)
        print_group("  unknown semantic color utilities", legacy_unknown_colors)

    if warnings:
        print()
        print("WARN: report-only drift indicators")
        print_warning_summary(
            "  routed pages using raw palette utilities",
            warnings.get("pages_using_raw_palette_utilities", []),
        )
        print_warning_summary(
            "  routed pages with visual scoped CSS",
            warnings.get("pages_with_visual_scoped_css", []),
        )

    if new_unknown_vars or new_unknown_colors:
        print()
        print("ERROR: new SPA style drift introduced outside the approved baseline.")
        print_group("  new unknown CSS vars", new_unknown_vars)
        print_group("  new unknown semantic color utilities", new_unknown_colors)
        return 1

    print()
    print("spa style guardrails: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
