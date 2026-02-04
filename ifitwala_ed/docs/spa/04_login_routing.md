# Login Routing & Portal Entry

> **Status:** Authoritative
> **Scope:** User login redirects based on role
> **Related:** `ifitwala_ed/api/users.py::redirect_user_to_entry_portal`

## Purpose

Define the authoritative routing logic for users after login. This ensures each user type lands on the appropriate surface based on their role.

## Routing Priority

When a user logs in, they are redirected based on the following priority:

| Order | User Type | Target | Home Page Set | Notes |
|-------|-----------|--------|---------------|-------|
| 1 | Student | `/sp` | Yes | Always takes precedence |
| 2 | Guardian | `/portal` | Yes | SPA router will route to `guardian-home` |
| 3 | Active Employee | `/portal/staff` | If unset | Respects explicit `/app` opt-in |
| 4 | Admissions Applicant | `/admissions` | If unset | Always to admissions portal |
| 5 | Others | (no redirect) | No | Falls through to Desk defaults |

## Guardian Routing (Fix #8)

**Issue:** Guardians with the "Guardian" role were not being redirected after login, causing them to land on Desk (`/app`) instead of the Guardian Portal.

**Solution:** Added explicit Guardian handling that:
1. Checks for "Guardian" role
2. Redirects to `/portal` (SPA handles further routing via `defaultPortal`)
3. Sets `User.home_page` to `/portal` for persistence
4. Respects explicit `home_page` choices if already set

## Implementation Notes

- Uses `frappe.local.response["home_page"]` for immediate redirect
- Uses `frappe.db.set_value("User", user, "home_page", path)` for persistence
- The `/portal` route uses `window.defaultPortal` to determine final SPA route
- Guardian role takes priority over Employee (a Guardian who is also an Employee will go to `/portal`)

## Security

- All checks use `frappe.get_roles()` for role verification
- Guardian link verified via `Guardian.user` field
- Student verified via `Student.student_user_id` field
- Employee verified via `Employee.user_id` + `employment_status = "Active"`
