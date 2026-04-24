from __future__ import annotations

from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import StubValidationError, import_fresh, stubbed_frappe


class TestNormalizeLegacyDesignationOrganizations(TestCase):
    def test_execute_maps_legacy_designations_when_single_real_organization_exists(self):
        updates: list[tuple[str, str, str, str, bool]] = []

        def get_all(doctype: str, filters=None, pluck=None, order_by=None, limit=None):
            if doctype == "Designation":
                self.assertEqual(filters, {"organization": "All Organizations"})
                self.assertEqual(pluck, "name")
                self.assertEqual(limit, 0)
                return ["Teacher", "Principal"]
            if doctype == "Organization":
                self.assertEqual(filters, {"name": ["!=", "All Organizations"]})
                self.assertEqual(pluck, "name")
                self.assertEqual(limit, 2)
                return ["ORG-ROOT"]
            raise AssertionError(f"Unexpected doctype: {doctype}")

        def set_value(doctype, name, fieldname, value, update_modified=False):
            updates.append((doctype, name, fieldname, value, update_modified))

        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: doctype in {"Designation", "Organization"}
            frappe.get_all = get_all
            frappe.db.set_value = set_value
            module = import_fresh("ifitwala_ed.patches.normalize_legacy_designation_organizations")

            module.execute()

        self.assertEqual(
            updates,
            [
                ("Designation", "Principal", "organization", "ORG-ROOT", False),
                ("Designation", "Teacher", "organization", "ORG-ROOT", False),
            ],
        )

    def test_execute_throws_when_legacy_mapping_is_ambiguous(self):
        updates: list[tuple] = []

        def get_all(doctype: str, **kwargs):
            if doctype == "Designation":
                return ["Teacher"]
            if doctype == "Organization":
                return ["ORG-A", "ORG-B"]
            raise AssertionError(f"Unexpected doctype: {doctype}")

        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: doctype in {"Designation", "Organization"}
            frappe.get_all = get_all
            frappe.db.set_value = lambda *args, **kwargs: updates.append(args)
            module = import_fresh("ifitwala_ed.patches.normalize_legacy_designation_organizations")

            with self.assertRaises(StubValidationError) as ctx:
                module.execute()

        self.assertIn("cannot be mapped automatically", str(ctx.exception))
        self.assertEqual(updates, [])

    def test_execute_throws_when_no_real_organization_exists(self):
        def get_all(doctype: str, **kwargs):
            if doctype == "Designation":
                return ["Teacher"]
            if doctype == "Organization":
                return []
            raise AssertionError(f"Unexpected doctype: {doctype}")

        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: doctype in {"Designation", "Organization"}
            frappe.get_all = get_all
            module = import_fresh("ifitwala_ed.patches.normalize_legacy_designation_organizations")

            with self.assertRaises(StubValidationError):
                module.execute()

    def test_execute_returns_when_required_tables_are_missing(self):
        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: False
            frappe.get_all = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_all should not run when required tables are missing")
            )
            module = import_fresh("ifitwala_ed.patches.normalize_legacy_designation_organizations")

            module.execute()
