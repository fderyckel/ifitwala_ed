from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _organization_chart_module():
    employee_utils = ModuleType("ifitwala_ed.utilities.employee_utils")
    employee_utils.get_descendant_organizations = lambda organization: [organization]
    employee_utils.get_user_base_org = lambda user: "ORG-1"

    helper_state = {"calls": []}
    image_utils = ModuleType("ifitwala_ed.utilities.image_utils")

    def apply_preferred_employee_images(
        rows,
        *,
        employee_field="id",
        image_field="image",
        slots=None,
        fallback_to_original=True,
        request_missing_derivatives=False,
    ):
        helper_state["calls"].append(
            {
                "employee_field": employee_field,
                "image_field": image_field,
                "slots": slots,
                "fallback_to_original": fallback_to_original,
                "request_missing_derivatives": request_missing_derivatives,
            }
        )
        resolved = []
        for row in rows:
            item = dict(row)
            if row.get(employee_field) == "EMP-0001":
                item[image_field] = "/files/employee/thumb_employee_1.webp"
            elif row.get(employee_field) == "EMP-0002":
                item[image_field] = "/files/employee/card_employee_2.webp"
            resolved.append(item)
        return resolved

    image_utils.apply_preferred_employee_images = apply_preferred_employee_images

    frappe_utils = ModuleType("frappe.utils")
    frappe_utils.get_datetime = lambda value: value
    frappe_utils.now = lambda: "2026-03-12 17:45:04"
    frappe_utils.now_datetime = lambda: "2026-03-12 17:45:04"
    frappe_utils.sanitize_html = lambda value, **kwargs: value
    frappe_utils.getdate = lambda value: value
    frappe_utils.formatdate = lambda value, fmt=None: f"formatted:{value}" if value else None

    with stubbed_frappe(
        extra_modules={
            "frappe.utils": frappe_utils,
            "ifitwala_ed.utilities.employee_utils": employee_utils,
            "ifitwala_ed.utilities.image_utils": image_utils,
        }
    ) as frappe:
        frappe.db.get_value = lambda doctype, name, fieldname=None, as_dict=False: {
            ("School", "SCH-1", "abbr"): "SCH",
            ("Organization", "ORG-1", "abbr"): "ORG",
        }.get((doctype, name, fieldname))
        frappe.db.has_column = lambda doctype, column: column == "phone_ext"
        yield import_fresh("ifitwala_ed.api.organization_chart"), helper_state


class TestOrganizationChartApi(TestCase):
    def test_get_org_chart_context_defaults_to_all_organizations(self):
        organizations = [
            {"name": "ORG-1", "organization_name": "Root Org"},
            {"name": "ORG-2", "organization_name": "Branch Org"},
        ]

        with _organization_chart_module() as (organization_chart, _helper_state):
            organization_chart.frappe.session.user = "staff@example.com"
            organization_chart.frappe.get_all = (
                lambda doctype, fields=None, filters=None, order_by=None, ignore_permissions=None: (
                    organizations if doctype == "Organization" else []
                )
            )

            payload = organization_chart.get_org_chart_context()

        self.assertEqual(payload["organizations"], organizations)
        self.assertIsNone(payload["default_organization"])

    def test_get_org_chart_children_applies_preferred_employee_images(self):
        root_rows = [
            {"name": "EMP-0001", "reports_to": None, "lft": 1},
            {"name": "EMP-0002", "reports_to": None, "lft": 5},
        ]
        detailed_rows = [
            {
                "id": "EMP-0001",
                "name": "Alice Admin",
                "first_name": "Alice",
                "preferred_name": "Ali",
                "title": "Principal",
                "school": "SCH-1",
                "organization": "ORG-1",
                "image": "/files/employee/original_employee_1.png",
                "professional_email": "alice@example.com",
                "phone_ext": "101",
                "date_of_joining": "2025-08-01",
                "reports_to": None,
                "lft": 1,
                "rgt": 4,
            },
            {
                "id": "EMP-0002",
                "name": "Bob Branch",
                "first_name": "Bob",
                "preferred_name": None,
                "title": "Coordinator",
                "school": "SCH-1",
                "organization": "ORG-1",
                "image": "/files/employee/original_employee_2.png",
                "professional_email": "bob@example.com",
                "phone_ext": "102",
                "date_of_joining": "2024-01-15",
                "reports_to": None,
                "lft": 5,
                "rgt": 6,
            },
        ]

        with _organization_chart_module() as (organization_chart, helper_state):
            calls = {"employee": 0}

            def fake_get_all(doctype, fields=None, filters=None, order_by=None, ignore_permissions=None):
                if doctype != "Employee":
                    return []
                calls["employee"] += 1
                if fields == ["name", "reports_to", "lft"]:
                    return root_rows
                return detailed_rows

            organization_chart.frappe.get_all = fake_get_all

            payload = organization_chart.get_org_chart_children(organization="ORG-1")

        self.assertEqual(
            [row["image"] for row in payload],
            [
                "/files/employee/thumb_employee_1.webp",
                "/files/employee/card_employee_2.webp",
            ],
        )
        self.assertEqual(payload[0]["school_abbr"], "SCH")
        self.assertEqual(payload[0]["organization_abbr"], "ORG")
        self.assertEqual(payload[0]["date_of_joining_label"], "formatted:2025-08-01")
        self.assertEqual(helper_state["calls"][0]["employee_field"], "id")
        self.assertEqual(helper_state["calls"][0]["image_field"], "image")
        self.assertEqual(
            helper_state["calls"][0]["slots"],
            ("profile_image_thumb", "profile_image_card", "profile_image_medium"),
        )
        self.assertFalse(helper_state["calls"][0]["fallback_to_original"])
        self.assertTrue(helper_state["calls"][0]["request_missing_derivatives"])
        self.assertEqual(calls["employee"], 2)

    def test_get_org_chart_tree_returns_helper_resolved_images(self):
        detailed_rows = [
            {
                "id": "EMP-0001",
                "name": "Alice Admin",
                "first_name": "Alice",
                "preferred_name": "Ali",
                "title": "Principal",
                "school": "SCH-1",
                "organization": "ORG-1",
                "image": "/files/employee/original_employee_1.png",
                "professional_email": "alice@example.com",
                "phone_ext": "101",
                "date_of_joining": "2025-08-01",
                "reports_to": None,
                "lft": 1,
                "rgt": 4,
            },
            {
                "id": "EMP-0002",
                "name": "Bob Branch",
                "first_name": "Bob",
                "preferred_name": None,
                "title": "Coordinator",
                "school": "SCH-1",
                "organization": "ORG-1",
                "image": "/files/employee/original_employee_2.png",
                "professional_email": "bob@example.com",
                "phone_ext": "102",
                "date_of_joining": "2024-01-15",
                "reports_to": "EMP-0001",
                "lft": 2,
                "rgt": 3,
            },
        ]

        with _organization_chart_module() as (organization_chart, helper_state):
            organization_chart.frappe.db.count = lambda doctype, filters=None: 2
            organization_chart.frappe.get_all = (
                lambda doctype, fields=None, filters=None, order_by=None, ignore_permissions=None: detailed_rows
            )

            payload = organization_chart.get_org_chart_tree(organization="ORG-1")

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["roots"], ["EMP-0001"])
        self.assertEqual(payload["total"], 2)
        self.assertEqual(payload["max_depth"], 2)
        self.assertEqual(
            [node["image"] for node in payload["nodes"]],
            ["/files/employee/thumb_employee_1.webp", "/files/employee/card_employee_2.webp"],
        )
        self.assertEqual(helper_state["calls"][0]["employee_field"], "id")
        self.assertEqual(helper_state["calls"][0]["image_field"], "image")
        self.assertEqual(
            helper_state["calls"][0]["slots"],
            ("profile_image_thumb", "profile_image_card", "profile_image_medium"),
        )
        self.assertFalse(helper_state["calls"][0]["fallback_to_original"])
        self.assertTrue(helper_state["calls"][0]["request_missing_derivatives"])
