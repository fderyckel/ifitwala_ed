# ifitwala_ed/website/vite_utils.py

import os
import json
import frappe

def get_vite_assets(
    app_name: str,
    manifest_paths: list[str],
    public_base: str,
    entry_keys: list[str] | None = None
) -> tuple[str, list[str], list[str]]:
    """
    Parses Vite manifest.json to find the entry point (JS, CSS, Preloads).
    
    Args:
        app_name: Name of the app (e.g. "ifitwala_ed")
        manifest_paths: List of absolute paths to potential manifest.json files
        public_base: URL prefix for assets (e.g. "/assets/ifitwala_ed/vite/")
        entry_keys: Optional list of keys to look for in the manifest to identify the entry point.
                    If None, defaults to ["index.html", "src/main.ts", "src/main.js"]
    
    Returns:
        tuple: (js_entry_url, css_files_urls, preload_files_urls)
    """
    
    # 1. Load Manifest
    manifest = {}
    for path in manifest_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                try:
                    manifest = json.load(f)
                    break 
                except json.JSONDecodeError:
                    continue
    
    if not manifest:
        # Fallback if no manifest found
        return (f"{public_base}main.js", [], [])

    # 2. Identify Entry Chunk
    entry = None
    if entry_keys:
        candidates = entry_keys
    else:
        candidates = ["index.html", "src/main.ts", "src/main.js"]

    for key in candidates:
        if key in manifest:
            entry = manifest[key]
            break
            
    # Fallback: find first chunk marked isEntry
    if not entry:
        for _, v in manifest.items():
            if isinstance(v, dict) and v.get("isEntry"):
                entry = v
                break
                
    if not entry:
        return (f"{public_base}main.js", [], [])

    # 3. Resolve URLs
    def _url(p: str) -> str:
        return f"{public_base}{p}"

    js_entry = _url(entry["file"])
    css_files = [_url(p) for p in entry.get("css", [])]

    # 4. Collect Preloads (recursive imports)
    preload = []
    seen = set()

    def walk(chunk: dict):
        for imp in (chunk.get("imports") or []):
            if imp in seen:
                continue
            seen.add(imp)
            sub = manifest.get(imp)
            if sub and "file" in sub:
                preload.append(_url(sub["file"]))
                walk(sub)

    if isinstance(entry, dict):
        walk(entry)

    return (js_entry, css_files, preload)
