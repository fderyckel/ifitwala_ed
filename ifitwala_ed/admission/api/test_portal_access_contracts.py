# ifitwala_ed/admission/api/test_portal_access_contracts.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt


import re
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.api.portal.access import _get_applicant_for_user, _require_admissions_applicant
from ifitwala_ed.admission.api.portal.enrollment import _portal_status_for, _read_only_for
from ifitwala_ed.admission.api.portal.snapshot import _derive_next_actions


class TestAdmissionsPortalAuthGuards(FrappeTestCase):
    def test_require_admissions_applicant_rejects_none_literal_as_unauthenticated(self):
        with patch("ifitwala_ed.admission.api.portal.access._session_user", return_value=""):
            with self.assertRaises(frappe.PermissionError):
                _require_admissions_applicant()

    def test_get_applicant_for_user_uses_canonical_applicant_user_only(self):
        def fake_get_all(doctype, **kwargs):
            self.assertEqual(doctype, "Student Applicant")
            filters = kwargs.get("filters") or {}
            if filters == {"name": ["in", ["APP-CANONICAL"]]}:
                return [{"name": "APP-CANONICAL"}]
            return []

        with (
            patch(
                "ifitwala_ed.admission.api.portal.access.get_admissions_portal_applicant_names_for_user",
                return_value=["APP-CANONICAL"],
            ) as mocked_names,
            patch("ifitwala_ed.admission.api.portal.access.frappe.get_all", side_effect=fake_get_all),
        ):
            row = _get_applicant_for_user(
                "applicant@example.com",
                fields=["name"],
            )

        mocked_names.assert_called_once_with(user="applicant@example.com", include_promoted=False)
        self.assertEqual(row.get("name"), "APP-CANONICAL")

    def test_get_applicant_for_user_rejects_email_only_matches(self):
        with (
            patch(
                "ifitwala_ed.admission.api.portal.access.get_admissions_portal_applicant_names_for_user",
                return_value=[],
            ) as mocked_names,
            patch(
                "ifitwala_ed.admission.api.portal.access.frappe.get_all",
                side_effect=AssertionError(
                    "no applicant row lookup should run when canonical access resolution is empty"
                ),
            ),
        ):
            with self.assertRaises(frappe.PermissionError):
                _get_applicant_for_user(
                    "applicant@example.com",
                    fields=["name"],
                )

        mocked_names.assert_called_once_with(user="applicant@example.com", include_promoted=False)


class TestAdmissionsPortalContracts(FrappeTestCase):
    def test_withdrawn_status_maps_to_portal_withdrawn(self):
        self.assertEqual(_portal_status_for("Withdrawn"), "Withdrawn")

    def test_withdrawn_status_is_read_only_with_reason(self):
        is_read_only, reason = _read_only_for("Withdrawn")
        self.assertTrue(is_read_only)
        self.assertTrue(bool(reason))

    def test_next_actions_documents_missing_is_blocking_upload(self):
        actions = _derive_next_actions(
            "In Progress",
            {
                "profile": {"ok": True},
                "policies": {"ok": True},
                "health": {"ok": True},
                "documents": {"ok": False, "missing": ["ID & Passport"], "unapproved": []},
            },
        )
        upload_actions = [row for row in actions if row.get("route_name") == "admissions-documents"]
        self.assertEqual(len(upload_actions), 1)
        self.assertEqual(upload_actions[0].get("label"), "Upload required documents")
        self.assertTrue(bool(upload_actions[0].get("is_blocking")))

    def test_next_actions_documents_under_review_is_not_blocking_upload(self):
        actions = _derive_next_actions(
            "In Progress",
            {
                "profile": {"ok": True},
                "policies": {"ok": True},
                "health": {"ok": True},
                "documents": {"ok": False, "missing": [], "unapproved": ["Transcripts"]},
            },
        )
        upload_actions = [row for row in actions if row.get("route_name") == "admissions-documents"]
        self.assertEqual(len(upload_actions), 1)
        self.assertEqual(upload_actions[0].get("label"), "Documents under review")
        self.assertFalse(bool(upload_actions[0].get("is_blocking")))

    def test_next_actions_recommendation_status_is_blocking_when_required(self):
        actions = _derive_next_actions(
            "In Progress",
            {
                "profile": {"ok": True},
                "policies": {"ok": True},
                "health": {"ok": True},
                "documents": {"ok": True, "missing": [], "unapproved": []},
                "recommendations": {"ok": False, "required_total": 1},
            },
        )
        recommendation_actions = [row for row in actions if row.get("route_name") == "admissions-status"]
        self.assertEqual(len(recommendation_actions), 1)
        self.assertTrue(bool(recommendation_actions[0].get("is_blocking")))


class TestContactPrivacyStaticGuards(FrappeTestCase):
    def test_sensitive_runtime_paths_do_not_serialize_person_records_with_fields_star(self):
        package_root = Path(__file__).resolve().parents[2]
        sensitive_paths = [
            "api/admissions_portal.py",
            "api/family_consent.py",
            "admission/admission_utils.py",
            "admission/doctype/student_applicant/student_applicant.py",
            "admission/doctype/inquiry/inquiry.py",
            "students/doctype/student/student.py",
            "students/doctype/guardian/guardian.py",
            "hr/doctype/employee/employee.py",
        ]
        sensitive_doctypes = ("Contact", "Guardian", "Student", "Student Applicant")
        forbidden: list[str] = []

        for relative_path in sensitive_paths:
            source = package_root.joinpath(relative_path).read_text(encoding="utf-8")
            for doctype in sensitive_doctypes:
                pattern = re.compile(
                    rf"frappe\.(?:db\.)?get_all\(\s*['\"]{re.escape(doctype)}['\"][\s\S]*?"
                    r"fields\s*=\s*\[\s*['\"]\*['\"]",
                    re.MULTILINE,
                )
                if pattern.search(source):
                    forbidden.append(f"{relative_path}: {doctype}")

        self.assertEqual(forbidden, [])
