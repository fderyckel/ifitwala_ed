# Copyright (c) 2024, fdR and Contributors
# See license.txt

# ifitwala_ed/schedule/doctype/student_group/test_student_group.py

from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.schedule.doctype.student_group.student_group import (
	build_in_clause_placeholders,
	descendants_inclusive,
	is_same_or_descendant,
)


class TestStudentGroup(TestCase):
	def test_build_in_clause_placeholders_matches_length(self):
		self.assertEqual(build_in_clause_placeholders(["A", "B", "C"]), "%s, %s, %s")

	def test_descendants_inclusive_returns_empty_without_school(self):
		self.assertEqual(descendants_inclusive(""), set())

	@patch("ifitwala_ed.schedule.doctype.student_group.student_group.get_school_lftrgt")
	def test_is_same_or_descendant_respects_nestedset_bounds(self, mock_lftrgt):
		def _bounds(school):
			mapping = {
				"ROOT": (1, 10),
				"CHILD": (2, 3),
				"SIBLING": (11, 12),
			}
			return mapping.get(school, (None, None))

		mock_lftrgt.side_effect = _bounds

		self.assertTrue(is_same_or_descendant("ROOT", "CHILD"))
		self.assertFalse(is_same_or_descendant("ROOT", "SIBLING"))
