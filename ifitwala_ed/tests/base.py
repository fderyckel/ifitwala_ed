# ifitwala_ed/tests/base.py

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase


class IfitwalaFrappeTestCase(FrappeTestCase):
	"""Common base class for Ifitwala tests.

	Keeps volatile cross-test flags deterministic.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.flags.enrollment_from_request = False

	def tearDown(self):
		frappe.flags.enrollment_from_request = False
		super().tearDown()
