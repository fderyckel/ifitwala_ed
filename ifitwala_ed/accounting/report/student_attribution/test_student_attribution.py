from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _student_attribution_module():
    fiscal_year_utils = ModuleType("ifitwala_ed.accounting.fiscal_year_utils")
    fiscal_year_utils.fill_date_range_from_fiscal_year = lambda filters, from_key="from_date", to_key="to_date": (
        None,
        None,
    )

    school_tree = ModuleType("ifitwala_ed.utilities.school_tree")
    school_tree.get_ancestor_schools = lambda school=None: [school] if school else []
    school_tree.get_descendant_schools = lambda school=None: []

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.accounting.fiscal_year_utils": fiscal_year_utils,
            "ifitwala_ed.utilities.school_tree": school_tree,
        }
    ) as frappe:
        frappe.db.sql = lambda *args, **kwargs: []
        yield import_fresh("ifitwala_ed.accounting.report.student_attribution.student_attribution")


class TestStudentAttribution(TestCase):
    def test_execute_uses_descendant_aware_school_filter(self):
        with (
            _student_attribution_module() as module,
            patch.object(module.frappe.db, "sql", return_value=[]) as mock_sql,
            patch.object(module, "get_descendant_schools", return_value=["SCH-PARENT", "SCH-CHILD"]),
            patch.object(module, "fill_date_range_from_fiscal_year", return_value=(None, None)),
        ):
            module.execute({"organization": "ORG-1", "school": "SCH-PARENT"})

        query, params = mock_sql.call_args.args[:2]
        self.assertIn("sii.school IN %(school_list)s", query)
        self.assertEqual(params["school_list"], ("SCH-PARENT", "SCH-CHILD"))
