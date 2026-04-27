from __future__ import annotations

from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestAdmissionsDriveContracts(TestCase):
    def test_health_vaccination_slot_sanitizes_user_entered_vaccine_names(self):
        with stubbed_frappe() as frappe:
            frappe.scrub = lambda value: str(value or "").replace(" ", "_").lower()

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Applicant Health Profile":
                    return {"name": "AHP-0001", "student_applicant": "APP-0001"}
                if doctype == "Student Applicant":
                    return {"organization": "ORG-1", "school": "SCH-1"}
                return None

            frappe.db.get_value = fake_get_value
            module = import_fresh("ifitwala_ed.integrations.drive.admissions")

            context = module.get_applicant_health_vaccination_context(
                {
                    "student_applicant": "APP-0001",
                    "applicant_health_profile": "AHP-0001",
                    "vaccine_name": "MMR / Booster (Dose #2)",
                    "date": "2023-02-13",
                    "row_index": 0,
                }
            )

        self.assertEqual(context["slot"], "health_vaccination_proof_mmr_booster_dose_2_2023-02-13")
