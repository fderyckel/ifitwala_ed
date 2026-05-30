# ifitwala_ed/admission/api/inquiry/dashboard.py

from __future__ import annotations

import frappe
from frappe.utils import add_days, nowdate

from ifitwala_ed.admission.api.inquiry.access import _ensure_access
from ifitwala_ed.admission.api.inquiry.dates import _resolve_window
from ifitwala_ed.admission.api.inquiry.scope import (
    SUBMITTED_LOCAL_EXPR,
    _apply_common_conditions,
    _rest_conditions,
)


def get_dashboard_data(filters=None):
    user = _ensure_access()
    parsed_filters = frappe.parse_json(filters) or {}
    return _build_dashboard_data(parsed_filters, user=user)


def _build_dashboard_data(filters: dict, user: str):
    """
    Returns summary + datasets for charts & cards.
    All queries parameterized (safe) and scoped by date window/filters.
    """
    # Use system timezone string for CONVERT_TZ
    site_tz = frappe.utils.get_system_timezone() or "UTC"

    where, params = _apply_common_conditions(filters, site_tz, user=user)
    rest_where, rest_params = _rest_conditions(filters, user=user)

    # --- Admission Settings: upcoming horizon (days) ---
    upcoming_horizon_days = frappe.db.get_single_value("Admission Settings", "followup_sla_days") or 7
    try:
        upcoming_horizon_days = int(upcoming_horizon_days)
    except Exception:
        upcoming_horizon_days = 7

    # ── counts
    total = frappe.db.sql(f"SELECT COUNT(*) FROM `tabInquiry` i WHERE {where}", params, as_dict=False)[0][0]

    contacted = frappe.db.sql(
        f"SELECT COUNT(*) FROM `tabInquiry` i WHERE {where} AND i.first_contacted_at IS NOT NULL", params, as_dict=False
    )[0][0]

    # 👇 FIX: use IS NULL (COALESCE ... IS NULL can never be true)
    params_with_today = {**params, "today": nowdate()}
    overdue_first = frappe.db.sql(
        """
        SELECT COUNT(*)
        FROM `tabInquiry` i
        WHERE {where}
            AND i.first_contacted_at IS NULL
            AND i.first_contact_due_on IS NOT NULL
            AND i.first_contact_due_on < %(today)s
        """.format(where=where),
        params_with_today,
        as_dict=False,
    )[0][0]

    # ── averages (overall window)
    avg_first = (
        frappe.db.sql(
            """
        SELECT AVG(i.response_hours_first_contact)
        FROM `tabInquiry` i
        WHERE {where} AND i.response_hours_first_contact IS NOT NULL
        """.format(where=where),
            params,
            as_dict=False,
        )[0][0]
        or 0
    )

    avg_from_assign = (
        frappe.db.sql(
            """
        SELECT AVG(i.response_hours_from_assign)
        FROM `tabInquiry` i
        WHERE {where} AND i.response_hours_from_assign IS NOT NULL
        """.format(where=where),
            params,
            as_dict=False,
        )[0][0]
        or 0
    )

    # ── trailing 30d smoothing (bounded by same filters + last 30 days cap)
    fd, td = _resolve_window(filters)
    params30 = dict(params)
    params30["from30"] = f"{max(add_days(td, -30), fd)} 00:00:00"
    params30["to30"] = f"{td} 23:59:59"

    avg_first_30 = (
        frappe.db.sql(
            f"""
        SELECT AVG(i.response_hours_first_contact)
        FROM `tabInquiry` i
        WHERE {SUBMITTED_LOCAL_EXPR} >= %(from30)s AND {SUBMITTED_LOCAL_EXPR} <= %(to30)s
            AND ({where})
            AND i.response_hours_first_contact IS NOT NULL
        """,
            params30,
            as_dict=False,
        )[0][0]
        or 0
    )

    avg_from_assign_30 = (
        frappe.db.sql(
            f"""
        SELECT AVG(i.response_hours_from_assign)
        FROM `tabInquiry` i
        WHERE {SUBMITTED_LOCAL_EXPR} >= %(from30)s AND {SUBMITTED_LOCAL_EXPR} <= %(to30)s
            AND ({where})
            AND i.response_hours_from_assign IS NOT NULL
        """,
            params30,
            as_dict=False,
        )[0][0]
        or 0
    )

    # ── monthly averages (YYYY-MM by submitted_at)
    monthly = frappe.db.sql(
        f"""
        SELECT DATE_FORMAT({SUBMITTED_LOCAL_EXPR}, '%%Y-%%m') AS ym,
                 AVG(i.response_hours_first_contact) AS a_first,
                 AVG(i.response_hours_from_assign)  AS a_assign
        FROM `tabInquiry` i
        WHERE {where}
        GROUP BY DATE_FORMAT({SUBMITTED_LOCAL_EXPR}, '%%Y-%%m')
        ORDER BY ym
        """,
        params,
        as_dict=True,
    )

    monthly_series = {
        "labels": [r["ym"] for r in monthly],
        "first_contact": [float(r["a_first"] or 0) for r in monthly],
        "from_assign": [float(r["a_assign"] or 0) for r in monthly],
    }

    # ── who has assignments (assignee distribution)
    assignees = frappe.db.sql(
        f"""
        SELECT i.assigned_to AS label, COUNT(*) AS value
        FROM `tabInquiry` i
        WHERE {where} AND i.assigned_to IS NOT NULL
        GROUP BY i.assigned_to ORDER BY value DESC
        """,
        params,
        as_dict=True,
    )

    # ── inquiry types (composition)
    types = frappe.db.sql(
        f"""
        SELECT COALESCE(i.type_of_inquiry, '—') AS label, COUNT(*) AS value
        FROM `tabInquiry` i
        WHERE {where}
        GROUP BY i.type_of_inquiry ORDER BY value DESC
        """,
        params,
        as_dict=True,
    )

    sources = frappe.db.sql(
        f"""
        SELECT COALESCE(NULLIF(i.source, ''), 'Unspecified') AS label, COUNT(*) AS value
        FROM `tabInquiry` i
        WHERE {where}
        GROUP BY COALESCE(NULLIF(i.source, ''), 'Unspecified')
        ORDER BY value DESC, label ASC
        """,
        params,
        as_dict=True,
    )

    # ── SLA Breach Monitor: Due Today & Upcoming (first contact)
    # compute horizon dates in Python to avoid `%d` casting issues
    today = nowdate()
    up_from = add_days(today, 1)  # tomorrow
    up_to = add_days(today, upcoming_horizon_days)

    due_today = frappe.db.sql(
        """
        SELECT COUNT(*)
        FROM `tabInquiry` i
        WHERE {where}
            AND i.first_contacted_at IS NULL
            AND DATE(i.first_contact_due_on) = %(today)s
        """.format(where=where),
        {**params, "today": today},
        as_dict=False,
    )[0][0]

    upcoming = frappe.db.sql(
        """
        SELECT COUNT(*)
        FROM `tabInquiry` i
        WHERE {where}
            AND i.first_contacted_at IS NULL
            AND DATE(i.first_contact_due_on) > %(up_from)s
            AND DATE(i.first_contact_due_on) <= %(up_to)s
        """.format(where=where),
        {**params, "up_from": up_from, "up_to": up_to},
        as_dict=False,
    )[0][0]

    lane_distribution = frappe.db.sql(
        f"""
        SELECT COALESCE(i.assignment_lane, 'Admission') AS label, COUNT(*) AS value
        FROM `tabInquiry` i
        WHERE {where}
        GROUP BY COALESCE(i.assignment_lane, 'Admission')
        ORDER BY label
        """,
        params,
        as_dict=True,
    )

    def _lane_metrics(lane: str) -> dict:
        lane_where = f"{where} AND COALESCE(i.assignment_lane, 'Admission') = %(lane)s"
        lane_params = {**params, "lane": lane}
        lane_total = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tabInquiry` i WHERE {lane_where}",
            lane_params,
            as_dict=False,
        )[0][0]
        lane_contacted = frappe.db.sql(
            f"SELECT COUNT(*) FROM `tabInquiry` i WHERE {lane_where} AND i.first_contacted_at IS NOT NULL",
            lane_params,
            as_dict=False,
        )[0][0]
        lane_overdue = frappe.db.sql(
            """
            SELECT COUNT(*)
            FROM `tabInquiry` i
            WHERE {lane_where}
                AND i.first_contacted_at IS NULL
                AND i.first_contact_due_on IS NOT NULL
                AND i.first_contact_due_on < %(today)s
            """.format(lane_where=lane_where),
            {**lane_params, "today": nowdate()},
            as_dict=False,
        )[0][0]
        lane_due_today = frappe.db.sql(
            """
            SELECT COUNT(*)
            FROM `tabInquiry` i
            WHERE {lane_where}
                AND i.first_contacted_at IS NULL
                AND DATE(i.first_contact_due_on) = %(today)s
            """.format(lane_where=lane_where),
            {**lane_params, "today": today},
            as_dict=False,
        )[0][0]
        lane_upcoming = frappe.db.sql(
            """
            SELECT COUNT(*)
            FROM `tabInquiry` i
            WHERE {lane_where}
                AND i.first_contacted_at IS NULL
                AND DATE(i.first_contact_due_on) > %(up_from)s
                AND DATE(i.first_contact_due_on) <= %(up_to)s
            """.format(lane_where=lane_where),
            {**lane_params, "up_from": up_from, "up_to": up_to},
            as_dict=False,
        )[0][0]
        lane_avg_intake = (
            frappe.db.sql(
                f"""
                SELECT AVG(i.intake_response_hours)
                FROM `tabInquiry` i
                WHERE {lane_where} AND i.intake_response_hours IS NOT NULL
                """,
                lane_params,
                as_dict=False,
            )[0][0]
            or 0
        )
        lane_avg_resolver = (
            frappe.db.sql(
                f"""
                SELECT AVG(i.resolver_response_hours)
                FROM `tabInquiry` i
                WHERE {lane_where} AND i.resolver_response_hours IS NOT NULL
                """,
                lane_params,
                as_dict=False,
            )[0][0]
            or 0
        )

        lane_params_30 = {**rest_params}
        lane_params_30["lane"] = lane
        lane_params_30["due_from30"] = f"{max(add_days(td, -30), fd)}"
        lane_params_30["due_to30"] = f"{td}"
        lane_den = frappe.db.sql(
            """
            SELECT COUNT(*)
            FROM `tabInquiry` i
            WHERE i.first_contact_due_on IS NOT NULL
                AND i.first_contact_due_on BETWEEN %(due_from30)s AND %(due_to30)s
                AND COALESCE(i.assignment_lane, 'Admission') = %(lane)s
                AND ({rest_where})
            """.format(rest_where=rest_where),
            lane_params_30,
            as_dict=False,
        )[0][0]
        lane_num = frappe.db.sql(
            """
            SELECT COUNT(*)
            FROM `tabInquiry` i
            WHERE i.first_contact_due_on IS NOT NULL
                AND i.first_contact_due_on BETWEEN %(due_from30)s AND %(due_to30)s
                AND i.first_contacted_at IS NOT NULL
                AND DATE(i.first_contacted_at) <= i.first_contact_due_on
                AND COALESCE(i.assignment_lane, 'Admission') = %(lane)s
                AND ({rest_where})
            """.format(rest_where=rest_where),
            lane_params_30,
            as_dict=False,
        )[0][0]
        lane_sla = round((float(lane_num) / lane_den * 100.0), 1) if lane_den else 0.0

        return {
            "counts": {
                "total": lane_total,
                "contacted": lane_contacted,
                "overdue_first_contact": lane_overdue,
                "due_today": lane_due_today,
                "upcoming": lane_upcoming,
            },
            "averages": {
                "intake_response_hours": round(float(lane_avg_intake), 2),
                "resolver_response_hours": round(float(lane_avg_resolver), 2),
            },
            "sla": {"pct_30d": lane_sla},
        }

    lane_breakdown = {
        "Admission": _lane_metrics("Admission"),
        "Staff": _lane_metrics("Staff"),
    }

    lane_monthly_rows = frappe.db.sql(
        f"""
        SELECT
            DATE_FORMAT({SUBMITTED_LOCAL_EXPR}, '%%Y-%%m') AS ym,
            COALESCE(i.assignment_lane, 'Admission') AS lane,
            AVG(i.resolver_response_hours) AS resolver_avg
        FROM `tabInquiry` i
        WHERE {where}
        GROUP BY ym, lane
        ORDER BY ym
        """,
        params,
        as_dict=True,
    )
    lane_monthly_labels = sorted({row.get("ym") for row in lane_monthly_rows if row.get("ym")})
    admission_map = {
        row.get("ym"): float(row.get("resolver_avg") or 0)
        for row in lane_monthly_rows
        if row.get("lane") == "Admission"
    }
    staff_map = {
        row.get("ym"): float(row.get("resolver_avg") or 0) for row in lane_monthly_rows if row.get("lane") == "Staff"
    }
    monthly_lane_series = {
        "labels": lane_monthly_labels,
        "admission": [round(admission_map.get(label, 0.0), 2) for label in lane_monthly_labels],
        "staff": [round(staff_map.get(label, 0.0), 2) for label in lane_monthly_labels],
    }

    # ── Pipeline by workflow_state
    pipeline = frappe.db.sql(
        f"""
        SELECT COALESCE(i.workflow_state, '—') AS label, COUNT(*) AS value
        FROM `tabInquiry` i
        WHERE {where}
        GROUP BY i.workflow_state
        ORDER BY value DESC
        """,
        params,
        as_dict=True,
    )

    # ── Weekly Inquiry Volume (week starts Monday)
    weekly = frappe.db.sql(
        f"""
        SELECT
            DATE_FORMAT(
                DATE_SUB(DATE({SUBMITTED_LOCAL_EXPR}), INTERVAL WEEKDAY({SUBMITTED_LOCAL_EXPR}) DAY),
                '%%Y-%%m-%%d'
            ) AS week_start,
            COUNT(*) AS value
        FROM `tabInquiry` i
        WHERE {where}
        GROUP BY week_start
        ORDER BY week_start
        """,
        params,
        as_dict=True,
    )
    weekly_series = {
        "labels": [r["week_start"] for r in weekly],
        "values": [int(r["value"] or 0) for r in weekly],
        "ranges": [
            {
                "from": r["week_start"] + " 00:00:00",
                "to": frappe.utils.formatdate(frappe.utils.add_days(r["week_start"], 6), "yyyy-mm-dd") + " 23:59:59",
            }
            for r in weekly
        ],
    }

    # ── SLA % (last 30d), measure by due_date falling in last30d, using non-date filters
    fd, td = _resolve_window(filters)
    params30 = {**rest_params}
    params30["due_from30"] = f"{max(add_days(td, -30), fd)}"
    params30["due_to30"] = f"{td}"

    sla_den = frappe.db.sql(
        """
        SELECT COUNT(*)
        FROM `tabInquiry` i
        WHERE i.first_contact_due_on IS NOT NULL
            AND i.first_contact_due_on BETWEEN %(due_from30)s AND %(due_to30)s
            AND ({rest_where})
        """.format(rest_where=rest_where),
        params30,
        as_dict=False,
    )[0][0]

    sla_num = frappe.db.sql(
        """
        SELECT COUNT(*)
        FROM `tabInquiry` i
        WHERE i.first_contact_due_on IS NOT NULL
            AND i.first_contact_due_on BETWEEN %(due_from30)s AND %(due_to30)s
            AND i.first_contacted_at IS NOT NULL
            AND DATE(i.first_contacted_at) <= i.first_contact_due_on
            AND ({rest_where})
        """.format(rest_where=rest_where),
        params30,
        as_dict=False,
    )[0][0]

    sla_pct_30 = round((float(sla_num) / sla_den * 100.0), 1) if sla_den else 0.0

    return {
        "counts": {
            "total": total,
            "contacted": contacted,
            "overdue_first_contact": overdue_first,
            "due_today": due_today,
            "upcoming": upcoming,
        },
        "pipeline_by_state": pipeline,
        "weekly_volume_series": weekly_series,
        "sla": {"pct_30d": sla_pct_30},
        "config": {"upcoming_horizon_days": upcoming_horizon_days},
        "averages": {
            "overall": {
                "first_contact_hours": round(float(avg_first), 2),
                "from_assign_hours": round(float(avg_from_assign), 2),
            },
            "last30d": {
                "first_contact_hours": round(float(avg_first_30), 2),
                "from_assign_hours": round(float(avg_from_assign_30), 2),
            },
        },
        "monthly_avg_series": monthly_series,
        "assignee_distribution": assignees,
        "type_distribution": types,
        "source_distribution": sources,
        "lane_distribution": lane_distribution,
        "lane_breakdown": lane_breakdown,
        "monthly_lane_series": monthly_lane_series,
    }
