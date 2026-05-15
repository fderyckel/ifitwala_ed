from unittest import TestCase

from ifitwala_ed.tests.e2e import scenario_names_for_pack


class TestE2EScenarios(TestCase):
    def test_smoke_pack_is_fixed_and_deterministic(self):
        self.assertEqual(
            scenario_names_for_pack("smoke"),
            (
                "hub_staff_basic",
                "hub_guardian_one_child",
                "admissions_profile_edit",
                "admissions_submit_blocked",
            ),
        )

    def test_unknown_pack_raises(self):
        with self.assertRaises(ValueError):
            scenario_names_for_pack("unknown")
