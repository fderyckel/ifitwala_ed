# ifitwala_ed/website/vite_utils.py

import json
import os


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
    manifest = {}
    for path in manifest_paths:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as handle:
            try:
                manifest = json.load(handle)
                break
            except json.JSONDecodeError:
                continue

    if not manifest:
        return (f"{public_base}main.js", [], [])

    candidates = entry_keys or ["index.html", "src/apps/portal/main.ts", "src/apps/portal/main.js"]
    entry = None
    for key in candidates:
        if key in manifest:
            entry = manifest[key]
            break

    if not entry:
        for _, candidate in manifest.items():
            if isinstance(candidate, dict) and candidate.get("isEntry"):
                entry = candidate
                break

    if not entry:
        return (f"{public_base}main.js", [], [])

    def _url(asset_path: str) -> str:
        return f"{public_base}{asset_path}"

    js_entry = _url(entry["file"])
    css_files = [_url(asset_path) for asset_path in entry.get("css", [])]

    preload_files = []
    seen_imports = set()

    def walk(chunk: dict):
        for imported in chunk.get("imports") or []:
            if imported in seen_imports:
                continue
            seen_imports.add(imported)
            sub = manifest.get(imported)
            if sub and "file" in sub:
                preload_files.append(_url(sub["file"]))
                walk(sub)

    if isinstance(entry, dict):
        walk(entry)

    return (js_entry, css_files, preload_files)
