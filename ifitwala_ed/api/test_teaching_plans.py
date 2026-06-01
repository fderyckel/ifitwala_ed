"""Teaching plan API tests are split across focused sibling modules.

See ``test_teaching_plans_*.py`` and ``teaching_plans_test_support.py``.
"""

from __future__ import annotations

import sys
import unittest

SPLIT_TEST_MODULES = (
    "ifitwala_ed.api.test_teaching_plans_student",
    "ifitwala_ed.api.test_teaching_plans_staff",
    "ifitwala_ed.api.test_teaching_plans_course_plan",
    "ifitwala_ed.api.test_teaching_plans_timeline",
    "ifitwala_ed.api.test_teaching_plans_read_models",
    "ifitwala_ed.api.test_teaching_plans_mutations",
)


def load_tests(loader, tests, pattern):
    if "ifitwala_ed.api.test_teaching_plans" not in sys.argv[1:]:
        return tests

    suite = unittest.TestSuite()
    for module_name in SPLIT_TEST_MODULES:
        suite.addTests(loader.loadTestsFromName(module_name))
    return suite
