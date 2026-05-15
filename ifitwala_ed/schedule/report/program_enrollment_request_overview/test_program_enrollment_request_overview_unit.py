# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import types
from unittest import TestCase
from unittest.mock import Mock

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


def _report_extra_modules(choice_module):
    frappe_utils = types.ModuleType("frappe.utils")
    frappe_utils.cint = lambda value: int(value or 0)

    basket_utils = types.ModuleType("ifitwala_ed.schedule.basket_group_utils")
    basket_utils.get_offering_course_semantics = lambda _offering: {}

    school_settings_utils = types.ModuleType("ifitwala_ed.school_settings.school_settings_utils")
    school_settings_utils.get_allowed_schools = lambda _user, school=None: [school] if school else []

    return {
        "frappe.utils": frappe_utils,
        "ifitwala_ed.schedule.basket_group_utils": basket_utils,
        "ifitwala_ed.schedule.program_enrollment_request_choice": choice_module,
        "ifitwala_ed.school_settings.school_settings_utils": school_settings_utils,
    }


class TestProgramEnrollmentRequestOverviewUnit(TestCase):
    def test_get_live_choice_states_delegates_to_batched_helper(self):
        choice_module = types.ModuleType("ifitwala_ed.schedule.program_enrollment_request_choice")
        choice_module.get_program_enrollment_request_live_choice_states = Mock(
            return_value={
                "PER-0001": {
                    "ready_for_submit": False,
                    "reasons": ["Choose at least one course in Group A."],
                }
            }
        )

        with stubbed_frappe(extra_modules=_report_extra_modules(choice_module)):
            module = import_fresh(
                "ifitwala_ed.schedule.report.program_enrollment_request_overview.program_enrollment_request_overview"
            )
            requests = [
                {
                    "name": "PER-0001",
                    "student": "STU-1",
                    "program_offering": "PO-1",
                    "request_status": "Draft",
                }
            ]

            result = module._get_live_choice_states(requests)

        choice_module.get_program_enrollment_request_live_choice_states.assert_called_once_with(requests)
        self.assertEqual(
            result,
            {
                "PER-0001": {
                    "ready_for_submit": False,
                    "reasons": ["Choose at least one course in Group A."],
                }
            },
        )
