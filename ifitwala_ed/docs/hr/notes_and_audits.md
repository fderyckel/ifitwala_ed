# Incident Postmortem: Governed Employee Image Uploads

**Date:** 2026-01-25  
**Scope:** Desk (Employee), governed uploads, file routing, derivative generation, UI avatar display

## Summary
Employee profile images uploaded via governed flow were saved, but the left column avatar loaded the **full-size original** and sometimes broke with 404s. This increased bandwidth and caused inconsistent UI behavior.

## Symptoms
1. `employee_image` pointed to `/files/Employee/<id>/...png` but the file did not exist on disk.
2. UI attempted to load `thumb_*.webp` from guessed paths and received 404s.
3. Sidebar avatar fell back to the original large image.

## Root Causes (Confirmed)
1. **Non-atomic routing**: `route_uploaded_file(...)` updated `file_url` even when the file move failed, producing broken URLs.
2. **Path guessing in UI**: client guessed derivative URLs instead of using canonical, classified URLs.
3. **No post-save verification**: governed upload endpoints updated `employee_image` without confirming the file existed on disk.
4. **Derivative governance gap**: image variants existed without consistent classification/slot tracking.

## Fixes Implemented
1. **Atomic routing**: `file_url` is updated only if the file exists at the destination.
2. **Post-save integrity check**: governed uploads verify the file exists before updating `employee_image`.
3. **Governed derivatives**: Employee derivatives (thumb/card/medium) are created via dispatcher and classified with:
   - `source_file` set to the original
   - slots: `profile_image_thumb`, `profile_image_card`, `profile_image_medium`
4. **UI canonicalization**: Employee form requests the canonical derivative URLs from the server and falls back only if needed.

## Preventive Rules (Actionable)
1. **Never guess URLs in UI**: always use server-provided canonical URLs for display.
2. **Never update `file_url` without verifying disk state**.
3. **All derivatives must be classified** (with `source_file` and explicit slot).
4. **Dispatcher orchestrates sequencing**: classification first, routing second, derivatives third.
5. **Deploy discipline**: when Desk JS changes, rebuild assets and clear cache before validating.

## Quick Checks for Future Incidents
1. **Employee image URL vs disk**:
   - Compare `Employee.employee_image` with file existence on disk.
2. **Classification presence**:
   - Ensure a `File Classification` exists for the original and each derivative.
3. **UI source**:
   - Verify UI loads from `get_employee_image_variants()` and not from guessed paths.

---

# HR Leave Domain Integration Audit

**Date:** 2026-02-11  
**Scope:** HR leave domain import from HRMS develop into Ifitwala HR (backend + desk)

## Change Summary
1. Imported leave-domain doctypes from HRMS develop snapshot.
2. Recorded upstream source commit for traceability (`5a3b657db2b9407f2a03ac78ce8cdf054a53bc1e`) and removed temporary vendor snapshot after stabilization.
3. Re-mapped tenancy and employee identity fields:
   - `company -> organization`
   - employee status checks to `employment_status`
   - employee display name to `employee_full_name`
4. Added controller-owned leave approval flow on `Leave Application` (no Workflow dependency).
5. Added `Employee Attendance` doctype for leave submit/cancel side-effects.
6. Added centralized leave permissions in `ifitwala_ed.hr.leave_permissions`.
7. Added scheduler hooks for expiry + earned leaves and feature-gated encashment.
8. Added minimal `HR Settings` singleton fields required by leave flows.

## Decisions Locked
1. Tenancy is organization-first with descendant scope for HR roles.
2. HR holiday source is Staff Calendar only (`Employee.current_holiday_lis`); no School Calendar fallback in leave logic.
3. Leave approval authorization is server-enforced in controller transitions, with override roles including `HR User`, `HR Manager`, `Academic Admin`, and `System Manager`.
4. Portal leave UI remains out of scope for this phase.
5. Leave Encashment is imported but disabled by default and inaccessible when the feature flag is off (`PQC = 1=0`, `has_permission = False`).

## Deferred or Follow-Up
1. Encashment payroll/accounting production enablement after mapping validation.
2. Expanded scenario tests for high-cardinality leave policy and scheduler cases.
3. Portal integration once backend behavior is stabilized.
