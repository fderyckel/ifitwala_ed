# Contact Permission Contract

Status: Active

This document is the canonical contract for Desk access to the native Frappe `Contact` DocType as governed by Ifitwala Ed setup code.

## 1. Contact Permission Contract

Status: Implemented

Code refs:
- `ifitwala_ed/setup/setup.py`
- `ifitwala_ed/utilities/contact_utils.py`

Test refs:
- `ifitwala_ed/setup/test_contact_permissions.py`

Rules:

1. `Contact` remains the native Frappe DocType; Ifitwala Ed governs role access through seeded `Custom DocPerm` rows rather than a custom clone.
2. The canonical Desk roles with read/write/create access on `Contact` are `Academic Admin`, `Academic Assistant`, `Assistant Admin`, `Accounts User`, `Accounts Manager`, `Admission Officer`, and `Admission Manager`.
3. Manager-level roles keep delete access on `Contact`: `Academic Admin`, `Academic Assistant`, `Assistant Admin`, `Accounts Manager`, and `Admission Manager`.
4. Non-manager editor roles keep no delete access on `Contact`: `Accounts User` and `Admission Officer`.
5. The permission seed must create any missing canonical roles before inserting `Custom DocPerm` rows, so migrate/setup never fails on a missing role record.
6. App-level Contact permission hooks must not narrow list visibility beyond the seeded DocPerm contract.

## 2. Runtime Enforcement

Status: Implemented

Code refs:
- `ifitwala_ed/setup/setup.py`
- `ifitwala_ed/hooks.py`
- `ifitwala_ed/utilities/contact_utils.py`
- `ifitwala_ed/patches/setup/p04_refresh_core_crm_permissions.py`

Test refs:
- `ifitwala_ed/setup/test_contact_permissions.py`

Rules:

1. Fresh installs seed the canonical `Contact` permissions through `grant_core_crm_permissions()` during `after_install`.
2. Existing sites are brought to the same contract by the post-model-sync patch `p04_refresh_core_crm_permissions`.
3. `grant_core_crm_permissions()` first ensures canonical roles exist, then seeds the `Custom DocPerm` rows.
4. Contact document-level permission checks defer to Frappe core once the seeded DocPerm rows exist.
5. Contact list visibility is not further constrained by app-specific query conditions.

## 3. Contract Matrix

Status: Implemented

Code refs:
- `ifitwala_ed/setup/setup.py`
- `ifitwala_ed/utilities/contact_utils.py`
- `ifitwala_ed/patches.txt`
- `ifitwala_ed/patches/setup/p04_refresh_core_crm_permissions.py`

Test refs:
- `ifitwala_ed/setup/test_contact_permissions.py`

| Concern | Canonical owner | Code refs | Test refs |
| --- | --- | --- | --- |
| Permission seed | `grant_core_crm_permissions` | `setup/setup.py` | `setup/test_contact_permissions.py` |
| Runtime permission hook | `contact_has_permission`, `contact_permission_query_conditions` | `utilities/contact_utils.py` | `setup/test_contact_permissions.py` |
| Existing-site rollout | post-model-sync patch | `patches/setup/p04_refresh_core_crm_permissions.py`, `patches.txt` | `setup/test_contact_permissions.py` |
