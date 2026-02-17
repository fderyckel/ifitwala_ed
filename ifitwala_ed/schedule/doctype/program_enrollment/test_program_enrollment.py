# Copyright (c) 2024, François de Ryckel and Contributors
# See license.txt

# ifitwala_ed/schedule/doctype/program_enrollment/test_program_enrollment.py

from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment import (
    _compute_effective_course_span,
    _offering_ay_names,
    _offering_ay_spine,
)


class TestProgramEnrollment(TestCase):
    @patch("frappe.get_all")
    def test_offering_ay_names_respects_child_row_order(self, mock_get_all):
        mock_get_all.return_value = ["AY-2025", "AY-2026"]

        result = _offering_ay_names("PO-TEST")

        self.assertEqual(result, ["AY-2025", "AY-2026"])
        mock_get_all.assert_called_once()

    @patch("frappe.get_all")
    def test_offering_ay_spine_uses_real_ay_bounds_and_skips_malformed(self, mock_get_all):
        mock_get_all.side_effect = [
            [
                {"academic_year": "AY-2025", "idx": 1},
                {"academic_year": "AY-2026", "idx": 2},
            ],
            [
                frappe._dict(
                    {
                        "name": "AY-2025",
                        "year_start_date": "2025-08-01",
                        "year_end_date": "2026-06-30",
                    }
                ),
            ],
        ]

        result = _offering_ay_spine("PO-TEST")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["academic_year"], "AY-2025")

    @patch("ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment._term_meta")
    @patch("ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment._ay_bounds_for")
    def test_compute_effective_course_span_clamps_to_term_bounds(self, mock_ay_bounds, mock_term_meta):
        mock_ay_bounds.side_effect = [
            ("2025-08-01", "2026-06-30"),
            ("2025-08-01", "2026-06-30"),
        ]
        mock_term_meta.side_effect = [
            (None, None, "2025-09-01", None),
            (None, None, None, "2026-05-15"),
        ]
        row = {
            "start_academic_year": "AY-2025",
            "end_academic_year": "AY-2025",
            "start_academic_term": "TERM-1",
            "end_academic_term": "TERM-2",
        }

        start_dt, end_dt = _compute_effective_course_span("PO-TEST", row)

        self.assertEqual(str(start_dt), "2025-09-01")
        self.assertEqual(str(end_dt), "2026-05-15")
