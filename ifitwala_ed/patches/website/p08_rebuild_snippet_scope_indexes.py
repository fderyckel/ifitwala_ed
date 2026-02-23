# ifitwala_ed/patches/website/p08_rebuild_snippet_scope_indexes.py

from ifitwala_ed.school_site.doctype.website_snippet.website_snippet import ensure_scope_indexes


def execute():
    ensure_scope_indexes()
