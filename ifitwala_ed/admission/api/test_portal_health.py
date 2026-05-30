# ifitwala_ed/admission/api/test_portal_health.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt


from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.api.portal.health import (
    get_applicant_health_impl as get_applicant_health,
)
from ifitwala_ed.admission.api.portal.health import (
    update_applicant_health_impl as update_applicant_health,
)
from ifitwala_ed.admission.api.portal_test_helpers import (
    AdmissionsPortalScenarioMixin,
)


class TestPortalHealth(AdmissionsPortalScenarioMixin, FrappeTestCase):
    def test_update_applicant_health_rejects_stale_expected_modified(self):
        frappe.set_user(self.applicant_user)
        initial = get_applicant_health(student_applicant=self.applicant.name)
        initial_modified = initial.get("record_modified") or ""

        fresh = update_applicant_health(
            student_applicant=self.applicant.name,
            expected_modified=initial_modified,
            vaccinations=[],
        )
        self.assertTrue(bool(fresh.get("record_modified")))

        with self.assertRaises(frappe.ValidationError):
            update_applicant_health(
                student_applicant=self.applicant.name,
                expected_modified=initial_modified,
                vaccinations=[],
            )

    def test_update_applicant_health_vaccination_upload_attaches_with_persisted_profile_name(self):
        captured: dict = {}

        def _capture_drive_upload(**kwargs):
            captured.update(kwargs)
            drive_file_id = f"DRV-FILE-{frappe.generate_hash(length=6)}"
            return {
                "file": f"FILE-{frappe.generate_hash(length=8)}",
                "file_url": f"/private/files/health-proof-{frappe.generate_hash(length=6)}.png",
                "drive_file_id": drive_file_id,
                "canonical_ref": f"drv:{self.organization}:{drive_file_id}",
                "student_applicant": kwargs.get("student_applicant"),
                "applicant_health_profile": kwargs.get("applicant_health_profile"),
            }

        frappe.set_user(self.applicant_user)
        with (
            patch(
                "ifitwala_ed.admission.api.portal.health.admission_api.upload_applicant_health_vaccination_proof",
                side_effect=_capture_drive_upload,
            ),
            patch("ifitwala_ed.admission.api.portal.health.materialize_health_review_assignments"),
        ):
            payload = update_applicant_health(
                student_applicant=self.applicant.name,
                blood_group="O Positive",
                allergies=True,
                food_allergies="No nuts",
                applicant_health_declared_complete=False,
                vaccinations=[
                    {
                        "vaccine_name": "MMR",
                        "date": "2020-03-04",
                        "vaccination_proof": "",
                        "additional_notes": "",
                        "vaccination_proof_content": self._tiny_png_base64(),
                        "vaccination_proof_file_name": "mmr-proof.png",
                    }
                ],
            )

        self.assertTrue(payload.get("ok"))
        self.assertIn("applicant_health_profile", captured)

        health_name = frappe.db.get_value(
            "Applicant Health Profile",
            {"student_applicant": self.applicant.name},
            "name",
        )
        self.assertTrue(bool(health_name))
        self.assertIsInstance(captured["applicant_health_profile"], str)
        self.assertEqual(captured["applicant_health_profile"], health_name)
        self.assertEqual(captured["student_applicant"], self.applicant.name)
        self.assertEqual(captured["vaccine_name"], "MMR")
        self.assertEqual(captured["date"], "2020-03-04")
        self.assertEqual(captured["row_index"], 0)
        self.assertEqual(captured["file_name"], "mmr-proof.png")
        self.assertEqual(captured["upload_source"], "SPA")
