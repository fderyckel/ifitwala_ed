<!-- ifitwala_ed/docs/website/04_builder_lite_plan.md -->
# Builder-Lite Plan (Locked Routing Model)

## Strict Namespace Ownership

| Namespace | Owner | Purpose |
| --- | --- | --- |
| `/` | Public home renderer | School-first public landing page |
| `/schools` | School directory renderer | Public multi-school directory |
| `/schools/*` | Custom website renderer | School marketing pages |
| `/apply/*` | Native Frappe Web Forms | Public forms |
| `/admissions/*` | Vue SPA (`www/admissions`) | Authenticated applicant portal |
| `/hub/*` | Vue SPA (`www/hub`) | Canonical authenticated portal namespaces |
| `/logout` | Website controller (`www/logout.py`) | Canonical logout endpoint with safe redirect |
| `/desk/*` | Frappe Desk | Internal administration |

## Non-Negotiable Routing Rules

1. No root catch-all (no `"/<path:route>" -> "website"`).
2. `/` renders the public homepage for the top public organization scope and must never default to login.
3. `/schools` remains the public directory/finder for published schools in that same scope.
4. No root-level school marketing slugs.
5. No exception-driven route ownership for webforms.
6. Legacy `/inquiry` redirects to canonical `/apply/inquiry`.

## Implementation Notes

1. `ifitwala_ed/www/index.py` renders the public homepage for `/` and the school directory for `/schools`.
2. `ifitwala_ed/website/utils.py::resolve_school_from_route` only accepts `/schools/{slug}/...`.
3. `ifitwala_ed/www/admissions/index.py` remains auth-guarded SPA entrypoint under `/admissions`.
4. Public form route is defined in Web Form JSON as `apply/inquiry`.
5. Portal SPA owns the canonical authenticated namespace under `/hub/*`.
6. `/logout` is owned by app website controller and must never rely on `?cmd=web_logout`.
