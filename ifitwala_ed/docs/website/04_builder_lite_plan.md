<!-- ifitwala_ed/docs/website/04_builder_lite_plan.md -->
# Builder-Lite Plan (Locked Routing Model)

## Strict Namespace Ownership

| Namespace | Owner | Purpose |
| --- | --- | --- |
| `/` | Organization landing renderer | Public multi-school landing |
| `/schools/*` | Custom website renderer | School marketing pages |
| `/apply/*` | Native Frappe Web Forms | Public forms |
| `/admissions/*` | Vue SPA (`www/admissions`) | Authenticated applicant portal |
| `/hub/*` | Vue SPA (`www/hub`) | Canonical authenticated portal namespaces |
| `/logout` | Website controller (`www/logout.py`) | Canonical logout endpoint with safe redirect |
| `/desk/*` | Frappe Desk | Internal administration |

## Non-Negotiable Routing Rules

1. No root catch-all (no `"/<path:route>" -> "website"`).
2. No default-school redirect from `/`.
3. No root-level school marketing slugs.
4. No exception-driven route ownership for webforms.
5. Legacy `/inquiry` redirects to canonical `/apply/inquiry`.

## Implementation Notes

1. `ifitwala_ed/www/index.py` renders organization landing directly.
2. `ifitwala_ed/website/utils.py::resolve_school_from_route` only accepts `/schools/{slug}/...`.
3. `ifitwala_ed/www/admissions/index.py` remains auth-guarded SPA entrypoint under `/admissions`.
4. Public form route is defined in Web Form JSON as `apply/inquiry`.
5. Portal SPA owns the canonical authenticated namespace under `/hub/*`.
7. `/logout` is owned by app website controller and must never rely on `?cmd=web_logout`.
