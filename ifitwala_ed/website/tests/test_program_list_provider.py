import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.tests.factories.organization import make_organization, make_school
from ifitwala_ed.website.providers import program_list as provider


class TestProgramListProvider(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        provider.invalidate_program_list_cache()

    def tearDown(self):
        provider.invalidate_program_list_cache()

    def test_published_program_with_draft_profile_returns_teaser_card(self):
        school, program = _make_public_school_with_published_program()

        payload = provider.get_context(
            school=frappe.get_doc("School", school.name),
            page=frappe._dict(),
            block_props={"school_scope": "current", "show_intro": 1, "limit": 6},
        )

        programs = payload["data"]["programs"]
        self.assertEqual(len(programs), 1)
        self.assertEqual(programs[0]["title"], program.program_name)
        self.assertTrue(programs[0]["is_teaser"])
        self.assertIsNone(programs[0]["url"])
        self.assertFalse(programs[0]["intro"])

    def test_published_program_with_published_profile_returns_detail_card(self):
        school, program = _make_public_school_with_published_program()
        profile_name = frappe.db.get_value(
            "Program Website Profile",
            {"school": school.name, "program": program.name},
            "name",
        )
        profile = frappe.get_doc("Program Website Profile", profile_name)
        profile.workflow_state = "Published"
        profile.save(ignore_permissions=True)
        provider.invalidate_program_list_cache()

        payload = provider.get_context(
            school=frappe.get_doc("School", school.name),
            page=frappe._dict(),
            block_props={"school_scope": "current", "show_intro": 1, "limit": 6},
        )

        programs = payload["data"]["programs"]
        self.assertEqual(len(programs), 1)
        self.assertFalse(programs[0]["is_teaser"])
        self.assertEqual(
            programs[0]["url"],
            f"/schools/{school.website_slug}/programs/{program.program_slug}",
        )
        self.assertTrue(programs[0]["intro"])


def _make_public_school_with_published_program():
    organization = make_organization(prefix="Website Program Org")
    school = make_school(organization.name, prefix="Website Program School")
    school.is_published = 1
    school.save(ignore_permissions=True)

    academic_year = frappe.get_doc(
        {
            "doctype": "Academic Year",
            "academic_year_name": f"AY {frappe.generate_hash(length=6)}",
            "school": school.name,
            "year_start_date": "2025-08-01",
            "year_end_date": "2026-06-30",
            "archived": 0,
            "visible_to_admission": 1,
        }
    ).insert(ignore_permissions=True)

    program = frappe.get_doc(
        {
            "doctype": "Program",
            "program_name": f"Website Program {frappe.generate_hash(length=6)}",
            "program_image": "/files/program-hero.jpg",
            "program_overview": "<p>Program overview for families.</p>",
        }
    ).insert(ignore_permissions=True)

    frappe.get_doc(
        {
            "doctype": "Program Offering",
            "program": program.name,
            "school": school.name,
            "status": "Planned",
            "offering_academic_years": [{"academic_year": academic_year.name}],
        }
    ).insert(ignore_permissions=True)

    program.reload()
    program.is_published = 1
    program.save(ignore_permissions=True)
    provider.invalidate_program_list_cache()

    school.reload()
    program.reload()
    return school, program
