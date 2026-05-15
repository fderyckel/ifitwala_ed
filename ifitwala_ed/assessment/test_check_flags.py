# ifitwala_ed/assessment/test_check_flags.py

from unittest import TestCase

from ifitwala_ed.assessment.check_flags import is_checked, to_check_value


class TestCheckFlags(TestCase):
    def test_is_checked_treats_falsey_check_values_as_disabled(self):
        for value in (None, "", "0", "false", "no", "off", 0, False):
            with self.subTest(value=value):
                self.assertFalse(is_checked(value))

    def test_is_checked_treats_truthy_check_values_as_enabled(self):
        for value in ("1", "true", "yes", "on", 1, True):
            with self.subTest(value=value):
                self.assertTrue(is_checked(value))

    def test_to_check_value_returns_integer_flags(self):
        self.assertEqual(to_check_value("1"), 1)
        self.assertEqual(to_check_value("0"), 0)
