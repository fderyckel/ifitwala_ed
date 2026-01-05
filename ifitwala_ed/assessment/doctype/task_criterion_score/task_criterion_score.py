# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TaskCriterionScore(Document):
	pass


def on_doctype_update():
	frappe.db.add_index("Task Criterion Score", ["parent", "parenttype", "student"])
