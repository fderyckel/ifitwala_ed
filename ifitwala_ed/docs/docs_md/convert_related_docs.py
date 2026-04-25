#!/usr/bin/env python3
"""Convert plain markdown Related Docs sections to <RelatedDocs> component."""

import re
from pathlib import Path

DOCS_DIR = Path("/Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/docs/docs_md")


def extract_slug_from_link(line):
    """Extract slug from a markdown link like [**Name**](/docs/en/slug/)."""
    match = re.search(r"/docs/en/([^/]+)/", line)
    if match:
        return match.group(1)
    return None


def convert_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # Find the Related Docs section
    rd_pattern = re.compile(
        r"^(## Related Docs\n)"
        r"((?:Status:.*?\n)?)"
        r"((?:Code refs:.*?\n)?)"
        r"((?:Test refs:.*?\n)?)"
        r"((?:\n)?)"
        r"((?:- \[.*?\n)+)",
        re.MULTILINE,
    )

    def replace_related_docs(m):
        # Extract all slugs from bullet list
        bullet_block = m.group(6)
        slugs = []
        for line in bullet_block.strip().split("\n"):
            slug = extract_slug_from_link(line)
            if slug:
                slugs.append(slug)

        if not slugs:
            return m.group(0)

        # Generate title based on category
        title = "Related Docs"

        # Build <RelatedDocs> component
        slugs_str = ",".join(slugs)
        result = f'## Related Docs\n\n<RelatedDocs\n  slugs="{slugs_str}"\n  title="{title}"\n/>\n'
        return result

    content = rd_pattern.sub(replace_related_docs, content)

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def main():
    changed = []
    for md_file in sorted(DOCS_DIR.glob("*.md")):
        if md_file.name.endswith(".py"):
            continue
        # Only process files that have Related Docs but no <RelatedDocs>
        with open(md_file, "r", encoding="utf-8") as f:
            text = f.read()
        if "## Related Docs" in text and "<RelatedDocs" not in text:
            if convert_file(md_file):
                changed.append(md_file.name)

    print(f"Files changed: {len(changed)}")
    for f in changed:
        print(f"  - {f}")


if __name__ == "__main__":
    main()
