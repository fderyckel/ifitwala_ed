# ifitwala_ed/api/test_admissions_review_facade.py

from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


def _record_whitelisted_methods(frappe):
    frappe.whitelisted = set()

    def whitelist(*args, **kwargs):
        def decorator(fn):
            frappe.whitelisted.add(fn)
            if kwargs.get("allow_guest"):
                fn.allow_guest = True
            return fn

        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return decorator(args[0])
        return decorator

    frappe.whitelist = whitelist


class TestAdmissionsReviewFacade(TestCase):
    def test_review_facade_reexports_admission_owned_endpoints(self):
        with stubbed_frappe() as frappe:
            _record_whitelisted_methods(frappe)
            review_endpoints = import_fresh("ifitwala_ed.admission.api.review_endpoints")
            admissions_review = import_fresh("ifitwala_ed.api.admissions_review")

            self.assertEqual(admissions_review.__all__, review_endpoints.__all__)
            for method_name in admissions_review.__all__:
                self.assertIs(getattr(admissions_review, method_name), getattr(review_endpoints, method_name))
                self.assertFalse(bool(getattr(getattr(admissions_review, method_name), "allow_guest", False)))

    def test_review_methods_remain_whitelisted(self):
        with stubbed_frappe() as frappe:
            _record_whitelisted_methods(frappe)
            admissions_review = import_fresh("ifitwala_ed.api.admissions_review")

            self.assertIn(admissions_review.review_applicant_document_submission, frappe.whitelisted)
            self.assertIn(admissions_review.set_document_requirement_override, frappe.whitelisted)

    def test_review_submission_delegates_with_cockpit_cache_invalidator(self):
        with stubbed_frappe() as frappe:
            _record_whitelisted_methods(frappe)
            import_fresh("ifitwala_ed.admission.api.review_endpoints")
            admissions_review = import_fresh("ifitwala_ed.api.admissions_review")

            with (
                patch(
                    "ifitwala_ed.admission.api.review_endpoints.review_applicant_document_submission_impl",
                    return_value={"documents": []},
                ) as impl,
                patch("ifitwala_ed.admission.api.review_endpoints.invalidate_admissions_cockpit_cache") as invalidate,
            ):
                self.assertEqual(
                    admissions_review.review_applicant_document_submission(
                        student_applicant="APP-1",
                        applicant_document_item="ITEM-1",
                        decision="Approved",
                        notes="Looks good",
                        client_request_id="REQ-1",
                    ),
                    {"documents": []},
                )

        impl.assert_called_once_with(
            student_applicant="APP-1",
            applicant_document_item="ITEM-1",
            decision="Approved",
            notes="Looks good",
            client_request_id="REQ-1",
            invalidate_cache=invalidate,
        )
