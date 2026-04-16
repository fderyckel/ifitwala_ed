# Address Template Seed Contract

Status: Active

This document is the canonical contract for the fallback native Frappe `Address Template` record seeded by Ifitwala Ed so Desk forms do not fail when linked addresses render on a fresh site.

## 1. Fresh-Site Seed

Status: Implemented

Code refs:
- `ifitwala_ed/setup/setup.py`

Test refs:
- `ifitwala_ed/setup/test_default_address_template.py`

Rules:

1. Fresh installs seed a native `Address Template` during `after_install` through `ensure_default_address_template()`.
2. The seeded record must use only verified native Frappe fields: `country`, `is_default`, and `template`.
3. The seeded template body must match the generic upstream Frappe address display template so address rendering works without app-specific assumptions.
4. If a default `Address Template` already exists, setup must not overwrite it.
5. If a site has no default template but an unused `Country` is available, setup creates a new default template instead of mutating existing country-specific templates.
6. If every `Country` already has a template, setup may promote an existing template to `is_default=1` rather than leaving the site in a crashing state.

## 2. Existing-Site Rollout

Status: Implemented

Code refs:
- `ifitwala_ed/patches/backfill_default_address_template.py`
- `ifitwala_ed/patches.txt`

Test refs:
- `ifitwala_ed/patches/test_backfill_default_address_template.py`

Rules:

1. Existing sites backfill the same fallback behavior through `ifitwala_ed.patches.backfill_default_address_template`.
2. The patch must no-op safely when the native `Address Template` table is unavailable.
3. The patch must delegate to the setup helper so fresh-install and migrate behavior stay identical.
