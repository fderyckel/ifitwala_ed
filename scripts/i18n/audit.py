#!/usr/bin/env python3
"""Audit Ifitwala Ed translation readiness.

The audit is intentionally static and Frappe-free. It reports the current
source-string state so later translation work can run from reproducible data
instead of one-off grep output.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import string
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / ".i18n-audit" / "current.json"

SCAN_EXTENSIONS = {".py", ".js", ".ts", ".vue", ".html", ".jinja", ".j2", ".json"}
EXCLUDED_DIRS = {
    ".git",
    ".i18n-audit",
    ".pytest_cache",
    ".venv",
    ".vite",
    "__pycache__",
    "dist",
    "node_modules",
}
EXCLUDED_PATH_PARTS = {
    ("ifitwala_ed", "docs"),
    ("ifitwala_ed", "public", "vite"),
    ("cypress", "screenshots"),
    ("cypress", "videos"),
}
TEST_PATH_MARKERS = {
    "__tests__",
    "fixtures",
    "tests",
    "test_support.py",
}
TEST_NAME_RE = re.compile(r"(^test_|_test\.|\.test\.|\.spec\.)")

TRANSLATABLE_JSON_KEYS = {
    "description",
    "documentation",
    "heading",
    "help",
    "intro",
    "label",
    "message",
    "module",
    "options",
    "print_heading",
    "read_only_message",
    "section_label",
    "shortcuts",
    "small_description",
    "subtitle",
    "title",
}

JS_CALL_RE = re.compile(r"\b__\s*\(")
JS_LITERAL_CALL_RE = re.compile(r"\b__\s*\(\s*([\"'`])((?:\\.|(?!\1).)*)\1", re.S)
JS_REPLACE_AFTER_TRANSLATION_RE = re.compile(
    r"\b__\s*\([^;\n]*\)\s*\.\s*(?:replace|format)\s*\(",
    re.S,
)
JS_RESERVED_ASSIGN_RE = re.compile(r"(?<![\w$.])(?:const|let|var)\s+(?:_|__)\b|(?<![\w$.=!<>])(?:_|__)\s*=(?!=)")
JS_RAW_FRAMEWORK_RE = re.compile(
    r"\b(?:frappe\.(?:throw|msgprint|show_alert|confirm|warn)|throw\s+new\s+Error)\s*"
    r"\(\s*([\"'`])((?:\\.|(?!\1).)*)\1",
    re.S,
)
VUE_TEXT_NODE_RE = re.compile(r">([^<>{}\n]*[A-Za-z][^<>{}]*)<")
RAW_ATTR_RE = re.compile(
    r"\s(?:label|title|placeholder|aria-label|alt)\s*=\s*([\"'])(?!\s*\{?__\()"
    r"([^\"']*[A-Za-z][^\"']*)\1"
)
HTML_TEXT_NODE_RE = re.compile(r">([^<>{}\n]*[A-Za-z][^<>{}]*)<")

NORMALIZATION_PATTERNS = (
    re.compile(r"^(?:Could not|Unable to|Couldn't) load\b", re.I),
    re.compile(r"^Loading\b", re.I),
    re.compile(r"^No .*(?:available|found|yet|right now|in this range|configured|recorded)", re.I),
    re.compile(r"^Back to\b", re.I),
    re.compile(r"^(?:Could not|Unable to|.* could not be) submit\b", re.I),
)
TECHNICAL_PATTERNS = (
    re.compile(r"\b[a-z]+_[a-z0-9_]+\b"),
    re.compile(r"\b(?:JSON|payload|doctype|DocType|traceback|Migration|installation|stack)\b"),
    re.compile(r"\bmust be a (?:list|dict|JSON object|JSON list)\b", re.I),
    re.compile(r"\b(?:Expected|Unexpected|missing envelope|server exception)\b"),
)
HTML_TAG_RE = re.compile(r"<[a-zA-Z][^>]*>")
PLACEHOLDER_RE = re.compile(r"\{[^{}]*\}")


@dataclass(frozen=True)
class Finding:
    bucket: str
    severity: str
    surface: str
    path: str
    line: int
    kind: str
    text: str
    detail: str


def repo_rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def has_path_sequence(parts: tuple[str, ...], sequence: tuple[str, ...]) -> bool:
    if len(sequence) > len(parts):
        return False
    for idx in range(0, len(parts) - len(sequence) + 1):
        if parts[idx : idx + len(sequence)] == sequence:
            return True
    return False


def is_test_path(path: Path, root: Path) -> bool:
    rel = repo_rel(path, root)
    parts = set(path.relative_to(root).parts)
    return bool(parts & TEST_PATH_MARKERS or TEST_NAME_RE.search(path.name) or "/test_" in rel)


def should_skip(path: Path, root: Path, include_tests: bool) -> bool:
    if path.suffix not in SCAN_EXTENSIONS or not path.is_file():
        return True
    rel_parts = path.relative_to(root).parts
    if any(part in EXCLUDED_DIRS for part in rel_parts):
        return True
    if any(has_path_sequence(rel_parts, sequence) for sequence in EXCLUDED_PATH_PARTS):
        return True
    if not include_tests and is_test_path(path, root):
        return True
    return False


def surface_for(path: Path, root: Path) -> str:
    rel_parts = path.relative_to(root).parts
    rel = repo_rel(path, root)
    if path.suffix == ".py":
        return "python_backend"
    if path.suffix == ".vue":
        return "vue_spa"
    if rel.startswith("ifitwala_ed/ui-spa/src/") and path.suffix in {".ts", ".js"}:
        return "vue_spa"
    if path.suffix in {".html", ".jinja", ".j2"}:
        return "templates"
    if path.suffix == ".json":
        if "doctype" in rel_parts:
            return "metadata_doctype"
        if "workspace" in rel_parts or "workspace_sidebar" in rel_parts or "desktop_icon" in rel_parts:
            return "metadata_workspace"
        if "report" in rel_parts:
            return "metadata_report"
        return "metadata_json"
    if path.suffix in {".js", ".ts"}:
        return "desk_js"
    return "other"


def line_for_pos(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def has_human_text(value: str) -> bool:
    return bool(re.search(r"[A-Za-z]", value))


def compact_text(value: str, limit: int = 180) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 3]}..."


def is_normalization_candidate(value: str) -> bool:
    text = compact_text(value)
    return any(pattern.search(text) for pattern in NORMALIZATION_PATTERNS)


def is_technical_or_internal(value: str) -> bool:
    text = compact_text(value)
    return any(pattern.search(text) for pattern in TECHNICAL_PATTERNS)


def classify_user_string(value: str, *, wrapped: bool = False, metadata: bool = False) -> tuple[str, str]:
    text = compact_text(value)
    if not text or not has_human_text(text):
        return "non_user_facing", "No human-language content detected."
    if metadata:
        return "safe_mechanical", "Frappe metadata string; should be covered by catalog extraction."
    if is_technical_or_internal(text):
        return "review_needed", "Looks technical or parameter-oriented; do not translate blindly."
    if is_normalization_candidate(text):
        return "normalization_first", "Matches a copy family that needs canonical English review."
    if wrapped:
        return "safe_mechanical", "Wrapped literal source string."
    return "safe_mechanical", "Unwrapped user-facing literal candidate."


def format_fields(value: str) -> list[str]:
    fields: list[str] = []
    formatter = string.Formatter()
    try:
        for _, field_name, _, _ in formatter.parse(value):
            if field_name is not None:
                fields.append(field_name)
    except ValueError:
        return ["<parse-error>"]
    return fields


def has_positional_or_invalid_format(value: str) -> bool:
    fields = format_fields(value)
    if "<parse-error>" in fields:
        return True
    for field_name in fields:
        root = field_name.split(".", 1)[0].split("[", 1)[0]
        if root == "" or root.isdigit():
            return True
    return False


def add_finding(
    findings: list[Finding],
    *,
    bucket: str,
    severity: str,
    surface: str,
    path: Path,
    root: Path,
    line: int,
    kind: str,
    text: str,
    detail: str,
) -> None:
    findings.append(
        Finding(
            bucket=bucket,
            severity=severity,
            surface=surface,
            path=repo_rel(path, root),
            line=max(line, 1),
            kind=kind,
            text=compact_text(text),
            detail=detail,
        )
    )


class PythonAuditVisitor(ast.NodeVisitor):
    def __init__(self, *, path: Path, root: Path, surface: str):
        self.path = path
        self.root = root
        self.surface = surface
        self.findings: list[Finding] = []
        self.wrapper_calls = 0
        self.literal_wrapper_calls = 0

    def _check_reserved_target(self, target: ast.AST) -> None:
        if isinstance(target, ast.Name) and target.id in {"_", "__"}:
            add_finding(
                self.findings,
                bucket="review_needed",
                severity="critical",
                surface=self.surface,
                path=self.path,
                root=self.root,
                line=getattr(target, "lineno", 1),
                kind="reserved_translation_alias_assignment",
                text=target.id,
                detail="`_` and `__` are reserved for translation functions.",
            )
        elif isinstance(target, (ast.Tuple, ast.List)):
            for item in target.elts:
                self._check_reserved_target(item)

    def visit_Assign(self, node: ast.Assign) -> Any:
        for target in node.targets:
            self._check_reserved_target(target)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> Any:
        self._check_reserved_target(node.target)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> Any:
        self._check_reserved_target(node.target)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> Any:
        if self._is_translation_call(node):
            self._audit_translation_call(node)
        if self._is_format_on_translation(node):
            self._audit_format_chain(node)
        if self._is_raw_frappe_message(node):
            self._audit_raw_frappe_message(node)
        self.generic_visit(node)

    @staticmethod
    def _is_translation_call(node: ast.Call) -> bool:
        return isinstance(node.func, ast.Name) and node.func.id in {"_", "__"}

    @staticmethod
    def _is_format_on_translation(node: ast.Call) -> bool:
        return (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "format"
            and isinstance(node.func.value, ast.Call)
            and isinstance(node.func.value.func, ast.Name)
            and node.func.value.func.id in {"_", "__"}
        )

    @staticmethod
    def _is_raw_frappe_message(node: ast.Call) -> bool:
        if not isinstance(node.func, ast.Attribute):
            return False
        if node.func.attr not in {"throw", "msgprint", "show_alert", "confirm", "warn"}:
            return False
        return isinstance(node.func.value, ast.Name) and node.func.value.id == "frappe"

    @staticmethod
    def _is_translation_expr(node: ast.AST) -> bool:
        return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"_", "__"}

    def _audit_translation_call(self, node: ast.Call) -> None:
        self.wrapper_calls += 1
        if not node.args:
            add_finding(
                self.findings,
                bucket="review_needed",
                severity="critical",
                surface=self.surface,
                path=self.path,
                root=self.root,
                line=node.lineno,
                kind="empty_translation_call",
                text="",
                detail="Translation call has no source string.",
            )
            return

        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            self.literal_wrapper_calls += 1
            text = first.value
            if has_positional_or_invalid_format(text):
                add_finding(
                    self.findings,
                    bucket="interpolation_risk",
                    severity="warning",
                    surface=self.surface,
                    path=self.path,
                    root=self.root,
                    line=node.lineno,
                    kind="positional_or_invalid_placeholder",
                    text=text,
                    detail="Use named placeholders in Python translatable strings.",
                )
            else:
                bucket, detail = classify_user_string(text, wrapped=True)
                if bucket in {"normalization_first", "review_needed"}:
                    add_finding(
                        self.findings,
                        bucket=bucket,
                        severity="info",
                        surface=self.surface,
                        path=self.path,
                        root=self.root,
                        line=node.lineno,
                        kind="wrapped_literal_review",
                        text=text,
                        detail=detail,
                    )
            return

        kind = "nonliteral_translation_source"
        detail = "Translation source must be a stable literal string."
        if isinstance(first, ast.JoinedStr):
            kind = "fstring_translation_source"
            detail = "Do not pass f-strings to translation functions."
        elif isinstance(first, ast.BinOp):
            kind = "concatenated_translation_source"
            detail = "Do not pass concatenated strings to translation functions."
        add_finding(
            self.findings,
            bucket="review_needed",
            severity="critical",
            surface=self.surface,
            path=self.path,
            root=self.root,
            line=node.lineno,
            kind=kind,
            text=ast.unparse(first) if hasattr(ast, "unparse") else "",
            detail=detail,
        )

    def _audit_format_chain(self, node: ast.Call) -> None:
        source_call = node.func.value
        if not source_call.args:
            return
        source = source_call.args[0]
        if not (isinstance(source, ast.Constant) and isinstance(source.value, str)):
            return
        text = source.value
        if node.args and not has_positional_or_invalid_format(text):
            add_finding(
                self.findings,
                bucket="interpolation_risk",
                severity="warning",
                surface=self.surface,
                path=self.path,
                root=self.root,
                line=node.lineno,
                kind="python_format_chain_needs_review",
                text=text,
                detail="Python translated format chains should use named placeholders and keyword format args.",
            )

    def _audit_raw_frappe_message(self, node: ast.Call) -> None:
        if not node.args:
            return
        first = node.args[0]
        if self._is_translation_expr(first):
            return
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            text = first.value
            bucket, detail = classify_user_string(text)
            add_finding(
                self.findings,
                bucket=bucket,
                severity="warning" if bucket == "safe_mechanical" else "info",
                surface=self.surface,
                path=self.path,
                root=self.root,
                line=node.lineno,
                kind="raw_frappe_message",
                text=text,
                detail=detail,
            )
        elif isinstance(first, (ast.JoinedStr, ast.BinOp, ast.Call)):
            add_finding(
                self.findings,
                bucket="review_needed",
                severity="info",
                surface=self.surface,
                path=self.path,
                root=self.root,
                line=node.lineno,
                kind="dynamic_raw_frappe_message",
                text=ast.unparse(first) if hasattr(ast, "unparse") else "",
                detail="Dynamic framework message needs manual user-facing review.",
            )


def audit_python(path: Path, root: Path, text: str, surface: str) -> tuple[list[Finding], dict[str, int]]:
    stats = {"wrapper_calls": 0, "literal_wrapper_calls": 0, "parse_errors": 0}
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        finding = Finding(
            bucket="review_needed",
            severity="critical",
            surface=surface,
            path=repo_rel(path, root),
            line=exc.lineno or 1,
            kind="python_parse_error",
            text=exc.msg,
            detail="Could not parse Python file for i18n audit.",
        )
        stats["parse_errors"] = 1
        return [finding], stats
    visitor = PythonAuditVisitor(path=path, root=root, surface=surface)
    visitor.visit(tree)
    stats["wrapper_calls"] = visitor.wrapper_calls
    stats["literal_wrapper_calls"] = visitor.literal_wrapper_calls
    return visitor.findings, stats


def audit_js_like(path: Path, root: Path, text: str, surface: str) -> tuple[list[Finding], dict[str, int]]:
    findings: list[Finding] = []
    stats = {
        "wrapper_calls": len(JS_CALL_RE.findall(text)),
        "literal_wrapper_calls": len(JS_LITERAL_CALL_RE.findall(text)),
    }

    for match in JS_CALL_RE.finditer(text):
        prefix = text[max(0, match.start() - 32) : match.start()]
        if re.search(r"(?:^|[\s;])(?:export\s+)?function\s+$", prefix):
            continue
        cursor = match.end()
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        if cursor >= len(text) or text[cursor] in {"'", '"', "`"}:
            continue
        add_finding(
            findings,
            bucket="review_needed",
            severity="critical",
            surface=surface,
            path=path,
            root=root,
            line=line_for_pos(text, match.start()),
            kind="nonliteral_translation_source",
            text=text[match.start() : min(cursor + 80, len(text))],
            detail="Translation source must be a stable literal string.",
        )

    for match in JS_LITERAL_CALL_RE.finditer(text):
        quote = match.group(1)
        source = match.group(2)
        line = line_for_pos(text, match.start())
        if quote == "`" and "${" in source:
            add_finding(
                findings,
                bucket="review_needed",
                severity="critical",
                surface=surface,
                path=path,
                root=root,
                line=line,
                kind="template_literal_translation_source",
                text=source,
                detail="Do not pass interpolated template literals to translation functions.",
            )
        elif quote == "`":
            add_finding(
                findings,
                bucket="interpolation_risk",
                severity="warning",
                surface=surface,
                path=path,
                root=root,
                line=line,
                kind="template_literal_translation_source",
                text=source,
                detail="Template literals should be reviewed before catalog extraction.",
            )
        elif PLACEHOLDER_RE.search(source) and ".replace" in text[match.end() : match.end() + 80]:
            add_finding(
                findings,
                bucket="interpolation_risk",
                severity="warning",
                surface=surface,
                path=path,
                root=root,
                line=line,
                kind="replace_after_translation",
                text=source,
                detail="Use translation helper arguments instead of post-translation replace().",
            )
        else:
            bucket, detail = classify_user_string(source, wrapped=True)
            if bucket in {"normalization_first", "review_needed"}:
                add_finding(
                    findings,
                    bucket=bucket,
                    severity="info",
                    surface=surface,
                    path=path,
                    root=root,
                    line=line,
                    kind="wrapped_literal_review",
                    text=source,
                    detail=detail,
                )

    for match in JS_REPLACE_AFTER_TRANSLATION_RE.finditer(text):
        add_finding(
            findings,
            bucket="interpolation_risk",
            severity="warning",
            surface=surface,
            path=path,
            root=root,
            line=line_for_pos(text, match.start()),
            kind="replace_or_format_after_translation",
            text=match.group(0),
            detail="Use translation helper arguments instead of string surgery after translation.",
        )

    for match in JS_RESERVED_ASSIGN_RE.finditer(text):
        add_finding(
            findings,
            bucket="review_needed",
            severity="critical",
            surface=surface,
            path=path,
            root=root,
            line=line_for_pos(text, match.start()),
            kind="reserved_translation_alias_assignment",
            text=match.group(0),
            detail="`_` and `__` are reserved for translation functions.",
        )

    for match in JS_RAW_FRAMEWORK_RE.finditer(text):
        source = match.group(2)
        bucket, detail = classify_user_string(source)
        add_finding(
            findings,
            bucket=bucket,
            severity="warning" if bucket == "safe_mechanical" else "info",
            surface=surface,
            path=path,
            root=root,
            line=line_for_pos(text, match.start()),
            kind="raw_framework_message",
            text=source,
            detail=detail,
        )

    return findings, stats


def strip_blocks(text: str, tag: str) -> str:
    return re.sub(rf"<{tag}(?:\s[^>]*)?>.*?</{tag}>", "", text, flags=re.I | re.S)


def audit_markup(path: Path, root: Path, text: str, surface: str) -> list[Finding]:
    findings: list[Finding] = []
    markup = strip_blocks(strip_blocks(text, "script"), "style")
    text_re = VUE_TEXT_NODE_RE if surface == "vue_spa" else HTML_TEXT_NODE_RE

    for match in text_re.finditer(markup):
        source = match.group(1)
        stripped = compact_text(source)
        if not stripped or stripped.startswith(("&", "#")):
            continue
        bucket, detail = classify_user_string(stripped)
        add_finding(
            findings,
            bucket=bucket,
            severity="warning" if bucket == "safe_mechanical" else "info",
            surface=surface,
            path=path,
            root=root,
            line=line_for_pos(markup, match.start()),
            kind="raw_markup_text",
            text=stripped,
            detail=detail,
        )

    for match in RAW_ATTR_RE.finditer(markup):
        source = match.group(2)
        bucket, detail = classify_user_string(source)
        add_finding(
            findings,
            bucket=bucket,
            severity="warning" if bucket == "safe_mechanical" else "info",
            surface=surface,
            path=path,
            root=root,
            line=line_for_pos(markup, match.start()),
            kind="raw_user_facing_attribute",
            text=source,
            detail=detail,
        )

    return findings


def audit_json(path: Path, root: Path, text: str, surface: str) -> tuple[list[Finding], dict[str, int]]:
    findings: list[Finding] = []
    stats = {"metadata_strings": 0, "parse_errors": 0}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        finding = Finding(
            bucket="review_needed",
            severity="critical",
            surface=surface,
            path=repo_rel(path, root),
            line=exc.lineno,
            kind="json_parse_error",
            text=exc.msg,
            detail="Could not parse JSON file for i18n audit.",
        )
        stats["parse_errors"] = 1
        return [finding], stats

    line_lookup: dict[str, int] = {}

    def line_for_value(value: str) -> int:
        if value not in line_lookup:
            quoted = json.dumps(value, ensure_ascii=False)
            idx = text.find(quoted)
            line_lookup[value] = line_for_pos(text, idx) if idx >= 0 else 1
        return line_lookup[value]

    def walk(value: Any, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                walk(child_value, str(child_key))
        elif isinstance(value, list):
            for child in value:
                walk(child, key)
        elif isinstance(value, str) and key in TRANSLATABLE_JSON_KEYS:
            if not has_human_text(value):
                return
            bucket, detail = classify_user_string(value, metadata=True)
            stats["metadata_strings"] += 1
            add_finding(
                findings,
                bucket=bucket,
                severity="info",
                surface=surface,
                path=path,
                root=root,
                line=line_for_value(value),
                kind=f"metadata_{key}",
                text=value,
                detail=detail,
            )

    walk(data)
    return findings, stats


def audit_file(path: Path, root: Path) -> tuple[list[Finding], dict[str, int]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    surface = surface_for(path, root)
    if path.suffix == ".py":
        return audit_python(path, root, text, surface)
    if path.suffix in {".js", ".ts"}:
        return audit_js_like(path, root, text, surface)
    if path.suffix == ".vue":
        findings, stats = audit_js_like(path, root, text, surface)
        findings.extend(audit_markup(path, root, text, surface))
        return findings, stats
    if path.suffix in {".html", ".jinja", ".j2"}:
        findings, stats = audit_js_like(path, root, text, surface)
        findings.extend(audit_markup(path, root, text, surface))
        return findings, stats
    if path.suffix == ".json":
        return audit_json(path, root, text, surface)
    return [], {}


def iter_scan_files(root: Path, include_tests: bool) -> list[Path]:
    app_root = root / "ifitwala_ed"
    if not app_root.exists():
        raise SystemExit(f"Could not find app root: {app_root}")
    files = [path for path in app_root.rglob("*") if not should_skip(path, root, include_tests=include_tests)]
    return sorted(files, key=lambda item: repo_rel(item, root))


def build_summary(
    files: list[Path],
    findings: list[Finding],
    stats_by_file: dict[str, dict[str, int]],
    root: Path,
) -> dict[str, Any]:
    by_surface: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "files": 0,
            "findings": 0,
            "buckets": Counter(),
            "severities": Counter(),
            "kinds": Counter(),
            "wrapper_calls": 0,
            "literal_wrapper_calls": 0,
            "metadata_strings": 0,
            "parse_errors": 0,
        }
    )

    for path in files:
        surface = surface_for(path, root)
        rel = repo_rel(path, root)
        row = by_surface[surface]
        row["files"] += 1
        for key, value in stats_by_file.get(rel, {}).items():
            row[key] = row.get(key, 0) + value

    for finding in findings:
        row = by_surface[finding.surface]
        row["findings"] += 1
        row["buckets"][finding.bucket] += 1
        row["severities"][finding.severity] += 1
        row["kinds"][finding.kind] += 1

    total_buckets = Counter(finding.bucket for finding in findings)
    total_severities = Counter(finding.severity for finding in findings)
    total_kinds = Counter(finding.kind for finding in findings)

    normalized = {}
    for surface, row in sorted(by_surface.items()):
        normalized[surface] = {
            **{key: value for key, value in row.items() if key not in {"buckets", "severities", "kinds"}},
            "buckets": dict(sorted(row["buckets"].items())),
            "severities": dict(sorted(row["severities"].items())),
            "kinds": dict(sorted(row["kinds"].items())),
        }

    return {
        "files_scanned": len(files),
        "findings": len(findings),
        "buckets": dict(sorted(total_buckets.items())),
        "severities": dict(sorted(total_severities.items())),
        "kinds": dict(sorted(total_kinds.items())),
        "by_surface": normalized,
    }


def write_report(output: Path, report: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def print_summary(report: dict[str, Any], output: Path) -> None:
    summary = report["summary"]
    print(f"i18n audit: scanned {summary['files_scanned']} files")
    print(f"i18n audit: {summary['findings']} findings")
    for bucket, count in summary["buckets"].items():
        print(f"  {bucket}: {count}")
    critical = summary["severities"].get("critical", 0)
    warning = summary["severities"].get("warning", 0)
    print(f"i18n audit: critical={critical} warning={warning}")
    print(f"i18n audit: wrote {output}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root. Defaults to this script's repository.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="JSON report path. Defaults to .i18n-audit/current.json.",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include tests and fixtures in the scan.",
    )
    parser.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Exit non-zero when critical findings are present.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    output = args.output
    if not output.is_absolute():
        output = root / output

    files = iter_scan_files(root, include_tests=args.include_tests)
    findings: list[Finding] = []
    stats_by_file: dict[str, dict[str, int]] = {}
    for path in files:
        file_findings, file_stats = audit_file(path, root)
        findings.extend(file_findings)
        stats_by_file[repo_rel(path, root)] = file_stats

    findings = sorted(findings, key=lambda item: (item.path, item.line, item.kind, item.text))
    report = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": root.as_posix(),
        "scan": {
            "include_tests": args.include_tests,
            "extensions": sorted(SCAN_EXTENSIONS),
            "excluded_dirs": sorted(EXCLUDED_DIRS),
            "excluded_path_parts": [list(parts) for parts in sorted(EXCLUDED_PATH_PARTS)],
        },
        "summary": build_summary(files, findings, stats_by_file, root),
        "findings": [asdict(finding) for finding in findings],
    }
    write_report(output, report)
    print_summary(report, output)

    if args.fail_on_critical and report["summary"]["severities"].get("critical", 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
