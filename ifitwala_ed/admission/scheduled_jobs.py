# ifitwala_ed/admission/scheduled_jobs.py

from __future__ import annotations

import frappe

from ifitwala_ed.admission.admission_utils import check_sla_breaches


def run_hourly_sla_sweep():
    """
    Scheduler-safe hourly entrypoint for admissions SLA recomputation.
    Kept thin so hooks point to a dedicated scheduled-jobs module.
    """
    logger = frappe.logger("sla_breaches", allow_site=True)
    try:
        return check_sla_breaches()
    except Exception:
        logger.exception("Hourly SLA sweep failed.")
        raise
