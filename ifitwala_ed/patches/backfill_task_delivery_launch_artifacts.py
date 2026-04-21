# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe


def execute():
    if not frappe.db.table_exists("Task Delivery") or not frappe.db.table_exists("Task Outcome"):
        return

    submitted_deliveries = frappe.get_all(
        "Task Delivery",
        filters={"docstatus": 1},
        fields=["name", "grading_mode", "rubric_version"],
        limit=100000,
    )
    if not submitted_deliveries:
        return

    delivery_names = [str(row.get("name") or "").strip() for row in submitted_deliveries if row.get("name")]
    if not delivery_names:
        return

    deliveries_with_outcomes = {
        str(name).strip()
        for name in frappe.get_all(
            "Task Outcome",
            filters={"task_delivery": ["in", delivery_names]},
            pluck="task_delivery",
            limit=0,
        )
        if str(name or "").strip()
    }

    for row in submitted_deliveries:
        delivery_name = str(row.get("name") or "").strip()
        if not delivery_name or not _needs_launch_backfill(row, deliveries_with_outcomes):
            continue

        try:
            frappe.get_doc("Task Delivery", delivery_name).materialize_roster()
        except Exception as exc:
            _log_backfill_failure(delivery_name=delivery_name, exc=exc)


def _needs_launch_backfill(row: dict, deliveries_with_outcomes: set[str]) -> bool:
    delivery_name = str(row.get("name") or "").strip()
    if not delivery_name:
        return False

    missing_outcomes = delivery_name not in deliveries_with_outcomes
    missing_rubric_snapshot = (row.get("grading_mode") or "").strip() == "Criteria" and not str(
        row.get("rubric_version") or ""
    ).strip()
    return missing_outcomes or missing_rubric_snapshot


def _log_backfill_failure(*, delivery_name: str, exc: Exception) -> None:
    log_error = getattr(frappe, "log_error", None)
    if not callable(log_error):
        return

    payload = {
        "error": "task_delivery_launch_artifact_backfill_failed",
        "task_delivery": delivery_name,
        "exception": repr(exc),
    }
    as_json = getattr(frappe, "as_json", None)
    message = as_json(payload, indent=2) if callable(as_json) else str(payload)
    log_error(message, "Task Delivery Launch Artifact Backfill Failed")
