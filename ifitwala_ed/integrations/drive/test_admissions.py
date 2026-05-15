from __future__ import annotations

from types import ModuleType, SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestAdmissionsDriveContracts(TestCase):
    def test_applicant_document_context_resolves_parent_from_item_without_document_type(self):
        admission_api = ModuleType("ifitwala_ed.admission.admissions_portal")
        captured_resolver_kwargs = {}

        def fake_resolve_applicant_document(**kwargs):
            captured_resolver_kwargs.update(kwargs)
            return SimpleNamespace(
                name="APP-DOC-0001",
                student_applicant="APP-0001",
                document_type="Transcript",
            )

        admission_api._resolve_applicant_document = fake_resolve_applicant_document
        admission_api._resolve_applicant_document_item = lambda **kwargs: SimpleNamespace(
            name="ADI-0001",
            item_key="aisl_2019",
            item_label="AISL transcript 2019",
        )

        admission_utils = ModuleType("ifitwala_ed.admission.admission_utils")
        admission_utils.get_applicant_document_slot_spec = lambda **kwargs: {
            "slot": "academic_report",
            "data_class": "academic",
            "purpose": "academic_report",
            "retention_policy": "until_school_exit_plus_6m",
        }

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.admission.admissions_portal": admission_api,
                "ifitwala_ed.admission.admission_utils": admission_utils,
            }
        ) as frappe:
            frappe.scrub = lambda value: str(value or "").replace(" ", "_").lower()

            def fake_get_value(doctype, name, fieldname=None, as_dict=False):
                if doctype == "Applicant Document Type":
                    return "transcript"
                if doctype == "Student Applicant":
                    return {"organization": "ORG-1", "school": "SCH-1"}
                return None

            frappe.db.get_value = fake_get_value
            module = import_fresh("ifitwala_ed.integrations.drive.admissions")

            context = module.get_applicant_document_context(
                {
                    "student_applicant": "APP-0001",
                    "applicant_document_item": "ADI-0001",
                    "filename_original": "transcript.pdf",
                }
            )

        self.assertEqual(captured_resolver_kwargs["applicant_document_item"], "ADI-0001")
        self.assertEqual(context["attached_name"], "ADI-0001")
        self.assertEqual(context["document_type"], "Transcript")

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
