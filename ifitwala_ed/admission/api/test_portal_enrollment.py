# ifitwala_ed/admission/api/test_portal_enrollment.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.admission.api.portal.enrollment import (
    accept_enrollment_offer_impl as accept_enrollment_offer,
)
from ifitwala_ed.admission.api.portal.enrollment import (
    decline_enrollment_offer_impl as decline_enrollment_offer,
)
from ifitwala_ed.admission.api.portal.enrollment import (
    get_applicant_enrollment_choices_impl as get_applicant_enrollment_choices,
)
from ifitwala_ed.admission.api.portal.enrollment import (
    update_applicant_enrollment_choices_impl as update_applicant_enrollment_choices,
)
from ifitwala_ed.admission.api.portal.session import get_admissions_session_impl as get_admissions_session
from ifitwala_ed.admission.api.portal.snapshot import get_applicant_snapshot_impl as get_applicant_snapshot
from ifitwala_ed.admission.api.portal_test_helpers import (
    AdmissionsPortalScenarioMixin,
    _policy_schema_available,
)
from ifitwala_ed.admission.doctype.applicant_enrollment_plan.applicant_enrollment_plan import (
    ensure_applicant_enrollment_plan,
)


class TestPortalEnrollment(AdmissionsPortalScenarioMixin, FrappeTestCase):
    def test_get_applicant_enrollment_choices_exposes_required_and_optional_offering_rows(self):
        core_group = f"Core Basket {frappe.generate_hash(length=6)}"
        humanities_group = f"Group 3 Humanities {frappe.generate_hash(length=6)}"
        sciences_group = f"Group 4 Sciences {frappe.generate_hash(length=6)}"
        context = self._create_offer_plan(
            status="Offer Sent",
            required_course_basket_groups=[core_group],
            optional_course_basket_groups=[humanities_group, sciences_group],
        )

        frappe.set_user(self.applicant_user)
        payload = get_applicant_enrollment_choices(student_applicant=self.applicant.name)

        self.assertEqual((payload.get("plan") or {}).get("status"), "Offer Sent")
        self.assertEqual((payload.get("summary") or {}).get("required_course_count"), 1)
        self.assertEqual((payload.get("summary") or {}).get("optional_course_count"), 1)

        rows_by_course = {row.get("course"): row for row in (payload.get("courses") or [])}
        self.assertTrue(bool(rows_by_course.get(context["required_course"].name, {}).get("required")))
        self.assertEqual(
            rows_by_course.get(context["optional_course"].name, {}).get("basket_groups"),
            [humanities_group, sciences_group],
        )

    def test_get_applicant_enrollment_choices_exposes_editable_applicant_intent_before_offer(self):
        humanities_group = f"Group 3 Humanities {frappe.generate_hash(length=6)}"
        context = self._create_offer_plan(
            status="Draft",
            optional_course_basket_groups=[humanities_group],
        )
        self.applicant.db_set("application_status", "In Progress", update_modified=False)

        frappe.set_user(self.applicant_user)
        payload = get_applicant_enrollment_choices(student_applicant=self.applicant.name)

        self.assertEqual(payload.get("source"), "applicant_intent")
        self.assertTrue((payload.get("plan") or {}).get("can_edit_choices"))
        rows_by_course = {row.get("course"): row for row in (payload.get("courses") or [])}
        self.assertIn(context["optional_course"].name, rows_by_course)

    def test_update_applicant_enrollment_choices_persists_applicant_intent_before_offer(self):
        humanities_group = f"Group 3 Humanities {frappe.generate_hash(length=6)}"
        context = self._create_offer_plan(
            status="Draft",
            optional_course_basket_groups=[humanities_group],
        )
        self.applicant.db_set("application_status", "In Progress", update_modified=False)

        frappe.set_user(self.applicant_user)
        payload = update_applicant_enrollment_choices(
            student_applicant=self.applicant.name,
            courses=[
                {
                    "course": context["optional_course"].name,
                    "applied_basket_group": humanities_group,
                    "choice_rank": 1,
                }
            ],
        )

        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("source"), "applicant_intent")
        self.applicant.reload()
        rows_by_course = {row.course: row for row in self.applicant.get("course_intents") or []}
        self.assertEqual(
            (rows_by_course[context["optional_course"].name].applied_basket_group or "").strip(),
            humanities_group,
        )
        self.assertEqual(rows_by_course[context["optional_course"].name].choice_rank, 1)

    def test_family_workspace_user_can_persist_applicant_course_intent(self):
        self._set_admissions_access_mode("Family Workspace")
        family_user = self._create_family_user()
        guardian = self._create_guardian_record(user=family_user.name, is_primary_guardian=True)
        self._link_family_guardian(self.applicant, guardian_name=guardian.name, user=family_user.name)
        humanities_group = f"Group 3 Humanities {frappe.generate_hash(length=6)}"
        context = self._create_offer_plan(
            status="Draft",
            optional_course_basket_groups=[humanities_group],
        )
        self.applicant.db_set("application_status", "In Progress", update_modified=False)

        frappe.set_user(family_user.name)
        payload = update_applicant_enrollment_choices(
            student_applicant=self.applicant.name,
            courses=[
                {
                    "course": context["optional_course"].name,
                    "applied_basket_group": humanities_group,
                }
            ],
        )

        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("source"), "applicant_intent")
        self.applicant.reload()
        self.assertEqual(
            (self.applicant.course_intents[0].applied_basket_group or "").strip(),
            humanities_group,
        )

    def test_applicant_enrollment_plan_seeds_from_applicant_course_intent(self):
        humanities_group = f"Group 3 Humanities {frappe.generate_hash(length=6)}"
        context = self._create_offer_plan(
            status="Draft",
            optional_course_basket_groups=[humanities_group],
        )
        frappe.delete_doc(
            "Applicant Enrollment Plan",
            context["plan"].name,
            force=1,
            ignore_permissions=True,
        )
        self.applicant.db_set("application_status", "In Progress", update_modified=False)

        frappe.set_user(self.applicant_user)
        update_applicant_enrollment_choices(
            student_applicant=self.applicant.name,
            courses=[
                {
                    "course": context["optional_course"].name,
                    "applied_basket_group": humanities_group,
                }
            ],
        )

        frappe.set_user("Administrator")
        plan = ensure_applicant_enrollment_plan(self.applicant.name)
        rows_by_course = {row.course: row for row in plan.get("courses") or []}
        self.assertEqual(
            (rows_by_course[context["optional_course"].name].applied_basket_group or "").strip(),
            humanities_group,
        )

    def test_update_applicant_enrollment_choices_persists_selection_and_required_group_resolution(self):
        required_group_one = f"Group 1 {frappe.generate_hash(length=6)}"
        required_group_two = f"Group 2 {frappe.generate_hash(length=6)}"
        humanities_group = f"Group 3 Humanities {frappe.generate_hash(length=6)}"
        context = self._create_offer_plan(
            status="Offer Sent",
            required_course_basket_groups=[required_group_one, required_group_two],
            optional_course_basket_groups=[humanities_group],
        )

        frappe.set_user(self.applicant_user)
        payload = update_applicant_enrollment_choices(
            student_applicant=self.applicant.name,
            courses=[
                {
                    "course": context["required_course"].name,
                    "applied_basket_group": required_group_one,
                },
                {
                    "course": context["optional_course"].name,
                    "applied_basket_group": humanities_group,
                    "choice_rank": 1,
                },
            ],
        )

        self.assertTrue(payload.get("ok"))
        self.assertEqual((payload.get("summary") or {}).get("selected_optional_count"), 1)

        context["plan"].reload()
        rows_by_course = {row.course: row for row in context["plan"].get("courses") or []}
        self.assertEqual(
            (rows_by_course[context["required_course"].name].applied_basket_group or "").strip(),
            required_group_one,
        )
        self.assertEqual(
            (rows_by_course[context["optional_course"].name].applied_basket_group or "").strip(),
            humanities_group,
        )
        self.assertEqual(rows_by_course[context["optional_course"].name].choice_rank, 1)

    def test_accept_enrollment_offer_requires_complete_course_choices(self):
        humanities_group = f"Group 3 Humanities {frappe.generate_hash(length=6)}"
        context = self._create_offer_plan(
            status="Offer Sent",
            optional_course_basket_groups=[humanities_group],
            enrollment_rules=[{"rule_type": "REQUIRE_GROUP_COVERAGE", "basket_group": humanities_group}],
        )

        frappe.set_user(self.applicant_user)
        with self.assertRaises(frappe.ValidationError):
            accept_enrollment_offer(student_applicant=self.applicant.name)

        update_applicant_enrollment_choices(
            student_applicant=self.applicant.name,
            courses=[
                {
                    "course": context["optional_course"].name,
                    "applied_basket_group": humanities_group,
                }
            ],
        )

        payload = accept_enrollment_offer(student_applicant=self.applicant.name)
        self.assertTrue(payload.get("ok"))
        self.assertEqual((payload.get("result") or {}).get("status"), "Offer Accepted")

    def test_accept_enrollment_offer_is_idempotent(self):
        self._create_offer_plan(status="Offer Sent")

        frappe.set_user(self.applicant_user)
        first = accept_enrollment_offer(student_applicant=self.applicant.name)
        second = accept_enrollment_offer(student_applicant=self.applicant.name)
        session_payload = get_admissions_session()

        self.assertTrue(first.get("ok"))
        self.assertTrue(second.get("ok"))
        self.assertEqual((first.get("result") or {}).get("status"), "Offer Accepted")
        self.assertEqual((second.get("result") or {}).get("status"), "Offer Accepted")
        self.assertEqual((session_payload.get("applicant") or {}).get("portal_status"), "Accepted")

    def test_decline_enrollment_offer_is_idempotent_and_visible_after_decline(self):
        if not _policy_schema_available():
            self.skipTest("Institutional Policy applies_to storage is required for admissions offer snapshot tests.")
        self._create_offer_plan(status="Offer Sent")

        frappe.set_user(self.applicant_user)
        first = decline_enrollment_offer(student_applicant=self.applicant.name)
        second = decline_enrollment_offer(student_applicant=self.applicant.name)
        session_payload = get_admissions_session()
        snapshot = get_applicant_snapshot(student_applicant=self.applicant.name)

        self.assertTrue(first.get("ok"))
        self.assertTrue(second.get("ok"))
        self.assertEqual((first.get("result") or {}).get("status"), "Offer Declined")
        self.assertEqual((second.get("result") or {}).get("status"), "Offer Declined")
        self.assertEqual((session_payload.get("applicant") or {}).get("portal_status"), "Declined")
        self.assertEqual((snapshot.get("enrollment_offer") or {}).get("status"), "Offer Declined")
