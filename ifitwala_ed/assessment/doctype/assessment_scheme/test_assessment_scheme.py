# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import StubValidationError, import_fresh, stubbed_frappe


class TestAssessmentScheme(TestCase):
    def test_weighted_category_scheme_requires_100_percent_active_final_weight(self):
        with stubbed_frappe():
            module = import_fresh("ifitwala_ed.assessment.doctype.assessment_scheme.assessment_scheme")
            scheme = module.AssessmentScheme()
            scheme.calculation_method = "Weighted Categories"
            scheme.status = "Draft"
            scheme.get = lambda fieldname: [
                types.SimpleNamespace(
                    assessment_category="Formative",
                    weight=40,
                    active=1,
                    include_in_final_grade=1,
                ),
                types.SimpleNamespace(
                    assessment_category="Summative",
                    weight=50,
                    active=1,
                    include_in_final_grade=1,
                ),
            ]

            with self.assertRaisesRegex(StubValidationError, "must total 100"):
                scheme.validate()

    def test_weighted_tasks_scheme_allows_categories_without_100_percent_weight(self):
        with stubbed_frappe():
            module = import_fresh("ifitwala_ed.assessment.doctype.assessment_scheme.assessment_scheme")
            scheme = module.AssessmentScheme()
            scheme.calculation_method = "Weighted Tasks"
            scheme.status = "Draft"
            scheme.get = lambda fieldname: [
                types.SimpleNamespace(
                    assessment_category="Practice",
                    weight=10,
                    active=1,
                    include_in_final_grade=1,
                )
            ]

            scheme.validate()
