# ifitwala_ed/website/vite_utils.py

from __future__ import annotations

import json
import os
import re

_VITE_MANIFEST_CACHE: dict[str, tuple[tuple[int, int], dict]] = {}
_WEBSITE_BUNDLE_CACHE: dict[str, tuple[tuple[int, int, int, int, int, int, int, int], tuple[str, str]]] = {}

_WEBSITE_JS_PATTERN = re.compile(r"^ifitwala_site\.[a-f0-9]{8}\.bundle\.js$")
_WEBSITE_CSS_PATTERN = re.compile(r"^ifitwala_site\.[a-f0-9]{8}\.bundle\.css$")


def _stat_fingerprint(path: str) -> tuple[int, int]:
    try:
        stat_result = os.stat(path)
    except FileNotFoundError:
        return (-1, -1)

    return (stat_result.st_mtime_ns, stat_result.st_size)


def _load_manifest(manifest_paths: list[str]) -> dict:
    for path in manifest_paths:
        fingerprint = _stat_fingerprint(path)
        if fingerprint == (-1, -1):
            continue
        cached = _VITE_MANIFEST_CACHE.get(path)
        if cached and cached[0] == fingerprint:
            return cached[1]

        with open(path, "r", encoding="utf-8") as handle:
            try:
                manifest = json.load(handle)
            except json.JSONDecodeError:
                if cached:
                    _VITE_MANIFEST_CACHE[path] = (fingerprint, cached[1])
                    return cached[1]
                continue

        _VITE_MANIFEST_CACHE[path] = (fingerprint, manifest)
        return manifest

    return {}


def _get_website_bundle_fingerprint(app_public_dir: str) -> tuple[int, int, int, int, int, int, int, int]:
    css_dir = os.path.join(app_public_dir, "css")
    js_dir = os.path.join(app_public_dir, "js")
    css_alias = os.path.join(css_dir, "ifitwala_site.bundle.css")
    js_alias = os.path.join(js_dir, "ifitwala_site.bundle.js")
    return (
        *_stat_fingerprint(css_dir),
        *_stat_fingerprint(js_dir),
        *_stat_fingerprint(css_alias),
        *_stat_fingerprint(js_alias),
    )


def _pick_latest_bundle_url(
    *,
    bundle_dir: str,
    filename_pattern: re.Pattern[str],
    fallback_url: str,
    public_base: str,
    asset_dir: str,
) -> str:
    latest_match: tuple[int, str] | None = None

    try:
        filenames = os.listdir(bundle_dir)
    except FileNotFoundError:
        return fallback_url

    for filename in filenames:
        if not filename_pattern.match(filename):
            continue
        mtime_ns = _stat_fingerprint(os.path.join(bundle_dir, filename))[0]
        candidate = (mtime_ns, filename)
        if latest_match is None or candidate > latest_match:
            latest_match = candidate

    if latest_match is None:
        return fallback_url

    return f"{public_base}{asset_dir}/{latest_match[1]}"


def get_vite_assets(
    app_name: str,
    manifest_paths: list[str],
    public_base: str,
    entry_keys: list[str] | None = None,
) -> tuple[str, list[str], list[str]]:
    """
    Parse a Vite manifest and return:
    (entry_js_url, css_urls, preload_js_urls).
    """
    manifest = _load_manifest(manifest_paths)

    if not manifest:
        return (f"{public_base}main.js", [], [])

    candidates = entry_keys or ["index.html", "src/apps/portal/main.ts", "src/apps/portal/main.js"]
    entry = None
    for key in candidates:
        if key in manifest:
            entry = manifest[key]
            break

    if not entry:
        for candidate in manifest.values():
            if isinstance(candidate, dict) and candidate.get("isEntry"):
                entry = candidate
                break

    if not entry:
        return (f"{public_base}main.js", [], [])

    def _url(asset_path: str) -> str:
        return f"{public_base}{asset_path}"

    js_entry = _url(entry["file"])

    css_files = []
    seen_css = set()
    preload_files = []
    seen_imports = set()

    def append_css(chunk: dict):
        for asset_path in chunk.get("css") or []:
            if asset_path in seen_css:
                continue
            seen_css.add(asset_path)
            css_files.append(_url(asset_path))

    append_css(entry)

    def walk(chunk: dict):
        for imported in chunk.get("imports") or []:
            if imported in seen_imports:
                continue
            seen_imports.add(imported)
            sub = manifest.get(imported)
            if sub and "file" in sub:
                preload_files.append(_url(sub["file"]))
                append_css(sub)
                walk(sub)

    if isinstance(entry, dict):
        walk(entry)

    return (js_entry, css_files, preload_files)


def get_website_bundle_urls(
    *,
    app_public_dir: str,
    public_base: str,
) -> tuple[str, str]:
    """
    Return the current hash-named website CSS/JS bundle URLs with stable aliases as fallback.
    """
    cache_key = os.path.abspath(app_public_dir)
    fingerprint = _get_website_bundle_fingerprint(cache_key)
    if fingerprint == (-1, -1, -1, -1, -1, -1, -1, -1):
        return (
            f"{public_base}css/ifitwala_site.bundle.css",
            f"{public_base}js/ifitwala_site.bundle.js",
        )

    cached = _WEBSITE_BUNDLE_CACHE.get(cache_key)
    if cached and cached[0] == fingerprint:
        return cached[1]

    css_dir = os.path.join(app_public_dir, "css")
    js_dir = os.path.join(app_public_dir, "js")
    css_href = _pick_latest_bundle_url(
        bundle_dir=css_dir,
        filename_pattern=_WEBSITE_CSS_PATTERN,
        fallback_url=f"{public_base}css/ifitwala_site.bundle.css",
        public_base=public_base,
        asset_dir="css",
    )
    js_href = _pick_latest_bundle_url(
        bundle_dir=js_dir,
        filename_pattern=_WEBSITE_JS_PATTERN,
        fallback_url=f"{public_base}js/ifitwala_site.bundle.js",
        public_base=public_base,
        asset_dir="js",
    )

    bundle_urls = (css_href, js_href)
    _WEBSITE_BUNDLE_CACHE[cache_key] = (fingerprint, bundle_urls)
    return bundle_urls
