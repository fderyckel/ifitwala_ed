# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe


def apply_official_outcome_from_contributions(outcome_id, policy=None):
	"""
	Recompute and persist the official outcome fields from contributions.

	This function is intentionally a stub in Step 3; the full implementation
	will be added when Task Contribution logic lands (Step 5).
	"""
	raise NotImplementedError("apply_official_outcome_from_contributions is implemented in Step 5.")


def set_procedural_status(outcome_id, status, note=None):
	"""
	Apply a procedural override safely and record an audit note.

	This function is intentionally a stub in Step 3; the full implementation
	will be added alongside procedural workflows in later steps.
	"""
	raise NotImplementedError("set_procedural_status is implemented in a later step.")
