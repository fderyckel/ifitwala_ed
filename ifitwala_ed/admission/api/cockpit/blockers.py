# ifitwala_ed/admission/api/cockpit/blockers.py

from __future__ import annotations

from frappe import _

from ifitwala_ed.admission.api.cockpit.access import _to_text
from ifitwala_ed.admission.api.cockpit.urls import _applicant_workspace_target, _target

BLOCKER_LABELS = {
    "missing_policies": "Missing Policies",
    "missing_documents": "Requirements Awaiting Submission",
    "documents_unapproved": "Requirements Needing Attention",
    "health_not_cleared": "Health Not Cleared",
    "profile_incomplete": "Profile Incomplete",
    "no_reviewer_assigned": "No Reviewer Assigned",
    "deposit_not_ready": "Deposit Not Ready",
}


def _build_blockers(
    *,
    snapshot: dict,
    application_status: str,
    open_assignments: int,
    applicant_name: str,
    first_open_assignment: dict | None,
) -> list[dict]:
    blockers: list[dict] = []

    policies = snapshot.get("policies") or {}
    documents = snapshot.get("documents") or {}
    health = snapshot.get("health") or {}
    profile = snapshot.get("profile") or {}

    applicant_target = _target(
        doctype="Student Applicant",
        name=applicant_name,
        target_label=_("Open applicant"),
    )

    if not policies.get("ok"):
        missing = policies.get("missing") or []
        missing_rows = policies.get("missing_rows") or []
        first_missing = missing_rows[0] if missing_rows else {}
        policy_version = _to_text(first_missing.get("policy_version"))

        target = (
            _target(
                doctype="Policy Version",
                name=policy_version,
                target_label=_("Open policy version"),
            )
            if policy_version
            else applicant_target
        )

        label = _("Missing policies") if not missing else _("Missing policies: {count}").format(count=len(missing))
        blockers.append(
            {
                "kind": "missing_policies",
                "label": label,
                "items": [str(item) for item in missing],
                **target,
            }
        )

    if not documents.get("ok"):
        missing = documents.get("missing") or []
        unapproved = documents.get("unapproved") or []
        missing_rows = documents.get("missing_rows") or []
        unapproved_rows = documents.get("unapproved_rows") or []

        if missing:
            first_missing = missing_rows[0] if missing_rows else {}
            missing_type = _to_text(first_missing.get("document_type"))

            target = (
                _applicant_workspace_target(
                    applicant_name=applicant_name,
                    document_type=missing_type,
                    target_label=_("Open requirement"),
                )
                if missing_type
                else applicant_target
            )

            blockers.append(
                {
                    "kind": "missing_documents",
                    "label": _("Requirements awaiting submission: {count}").format(count=len(missing)),
                    "items": [str(item) for item in missing],
                    **target,
                }
            )

        if unapproved:
            first_unapproved = unapproved_rows[0] if unapproved_rows else {}
            applicant_document = _to_text(first_unapproved.get("applicant_document"))
            document_type = _to_text(first_unapproved.get("document_type"))
            document_item = _to_text(first_unapproved.get("applicant_document_item"))
            review_status = _to_text(first_unapproved.get("review_status"))

            if review_status == "Rejected":
                label = _("Requirements awaiting resubmission: {count}").format(count=len(unapproved))
                target_label = _("Open requirement")
                document_item = None
            else:
                label = _("Submitted files awaiting review: {count}").format(count=len(unapproved))
                target_label = _("Open submission review")

            target = (
                _applicant_workspace_target(
                    applicant_name=applicant_name,
                    document_type=document_type,
                    applicant_document=applicant_document,
                    document_item=document_item,
                    target_label=target_label,
                )
                if applicant_document or document_type
                else applicant_target
            )

            blockers.append(
                {
                    "kind": "documents_unapproved",
                    "label": label,
                    "items": [str(item) for item in unapproved],
                    **target,
                }
            )

    if bool(health.get("required_for_approval", True)) and not health.get("ok"):
        health_profile = _to_text(health.get("profile_name"))
        target = (
            _target(
                doctype="Applicant Health Profile",
                name=health_profile,
                target_label=_("Open health profile"),
            )
            if health_profile
            else _target(
                doctype="Applicant Health Profile",
                is_new=True,
                params={"student_applicant": applicant_name},
                target_label=_("Create health profile"),
            )
        )

        blockers.append(
            {
                "kind": "health_not_cleared",
                "label": _("Health profile is missing or not cleared"),
                "items": [],
                **target,
            }
        )

    if not profile.get("ok"):
        missing = profile.get("missing") or []
        blockers.append(
            {
                "kind": "profile_incomplete",
                "label": _("Profile information incomplete"),
                "items": [str(item) for item in missing],
                **applicant_target,
            }
        )

    status = _to_text(application_status)
    if status in {"Submitted", "Under Review"} and open_assignments == 0:
        if first_open_assignment and _to_text(first_open_assignment.get("name")):
            target = _target(
                doctype="Applicant Review Assignment",
                name=_to_text(first_open_assignment.get("name")),
                target_label=_("Open review assignment"),
            )
        else:
            target = _target(
                doctype="Applicant Review Assignment",
                is_new=True,
                params={
                    "target_type": "Student Applicant",
                    "target_name": applicant_name,
                    "student_applicant": applicant_name,
                },
                target_label=_("Create review assignment"),
            )

        blockers.append(
            {
                "kind": "no_reviewer_assigned",
                "label": _("No reviewer assignment is open"),
                "items": [],
                **target,
            }
        )

    return blockers
