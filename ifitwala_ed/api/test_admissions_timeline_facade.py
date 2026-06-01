# ifitwala_ed/api/test_admissions_timeline_facade.py

import types
from unittest import TestCase

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


class TestAdmissionsTimelineFacade(TestCase):
    def test_timeline_facade_reexports_admission_owned_endpoint(self):
        with stubbed_frappe() as frappe:
            _record_whitelisted_methods(frappe)
            endpoints = import_fresh("ifitwala_ed.admission.api.timeline.endpoints")
            admissions_timeline = import_fresh("ifitwala_ed.api.admissions_timeline")

            self.assertEqual(admissions_timeline.__all__, endpoints.__all__)
            for method_name in admissions_timeline.__all__:
                self.assertIs(getattr(admissions_timeline, method_name), getattr(endpoints, method_name))
                self.assertFalse(bool(getattr(getattr(admissions_timeline, method_name), "allow_guest", False)))

    def test_timeline_context_endpoint_remains_whitelisted(self):
        with stubbed_frappe() as frappe:
            _record_whitelisted_methods(frappe)
            admissions_timeline = import_fresh("ifitwala_ed.api.admissions_timeline")

            self.assertIn(admissions_timeline.get_admissions_timeline_context, frappe.whitelisted)

    def test_timeline_context_delegates_to_domain_implementation(self):
        calls: dict[str, object] = {}
        context_module = types.ModuleType("ifitwala_ed.admission.api.timeline.context")

        def fake_get_admissions_timeline_context_impl(*, context_doctype=None, context_name=None, limit=None):
            calls["context_doctype"] = context_doctype
            calls["context_name"] = context_name
            calls["limit"] = limit
            return {"items": []}

        context_module.get_admissions_timeline_context_impl = fake_get_admissions_timeline_context_impl

        with stubbed_frappe(extra_modules={"ifitwala_ed.admission.api.timeline.context": context_module}) as frappe:
            _record_whitelisted_methods(frappe)
            admissions_timeline = import_fresh("ifitwala_ed.api.admissions_timeline")

            self.assertEqual(
                admissions_timeline.get_admissions_timeline_context(
                    context_doctype="Student Applicant",
                    context_name="APP-1",
                    limit="30",
                ),
                {"items": []},
            )

        self.assertEqual(calls["context_doctype"], "Student Applicant")
        self.assertEqual(calls["context_name"], "APP-1")
        self.assertEqual(calls["limit"], "30")
