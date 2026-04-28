from datetime import timedelta
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, getdate, now_datetime, nowdate

from ifitwala_ed.admission.admission_utils import get_admissions_file_staff_scope
from ifitwala_ed.utilities.employee_utils import get_schools_for_organization_scope
from ifitwala_ed.utilities.school_tree import get_descendant_schools

SUBMITTED_LOCAL_EXPR = "i.submitted_at"


def _ay_bounds(academic_year: str):
    if not academic_year:
        return None, None
    start, end = frappe.db.get_value("Academic Year", academic_year, ["year_start_date", "year_end_date"])
    return start, end


PRESET_ALIASES = {
    "last_7": "7d",
    "last_30": "30d",
    "last_90": "90d",
    "ytd": "year",
    "all_time": "all",
}


def _normalize_preset(value: str | None):
    if not value:
        return None
    preset = value.strip().lower()
    return PRESET_ALIASES.get(preset, preset)


def _preset_bounds(preset: str):
    preset = _normalize_preset(preset)
    if not preset:
        return None, None

    today = getdate(nowdate())
    if preset == "7d":
        return add_days(today, -7), today
    if preset == "30d":
        return add_days(today, -30), today
    if preset == "90d":
        return add_days(today, -90), today
    if preset == "year":
        return getdate(f"{today.year}-01-01"), today
    if preset == "all":
        return getdate("1900-01-01"), today
    return None, None


def _resolve_window(filters: dict):
    mode = (filters.get("date_mode") or "").strip()
    preset = filters.get("date_preset")
    fd = filters.get("from_date")
    td = filters.get("to_date")
    ay = filters.get("academic_year")

    if mode == "preset" and preset:
        fd, td = _preset_bounds(preset)
    elif mode == "academic_year" and ay:
        fd, td = _ay_bounds(ay)
    elif mode == "custom" and fd and td:
        fd, td = fd, td
    else:
        td = getdate(nowdate())
        fd = add_days(td, -365)

    if not fd or not td:
        td = getdate(nowdate())
        fd = add_days(td, -365)

    return getdate(fd), getdate(td)


ALLOWED_ANALYTICS_ROLES = {
    "Academic Admin",
    "Admission Officer",
    "Admission Manager",
    "System Manager",
    "Administrator",
}


def _ensure_access(user: str | None = None) -> str:
    """Gate analytics to authorized staff roles."""
    user = user or frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You need to sign in to access Inquiry Analytics."), frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    if roles & ALLOWED_ANALYTICS_ROLES:
        return user

    frappe.throw(_("You do not have permission to access Inquiry Analytics."), frappe.PermissionError)
    return user


def _clean_values(values) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        text = (value or "").strip()
        if not text or text in seen:
            continue
        cleaned.append(text)
        seen.add(text)
    return cleaned


def _get_descendant_organizations(root_org: str):
    if not root_org:
        return []
    org_bounds = frappe.db.get_value("Organization", root_org, ["lft", "rgt"], as_dict=True)
    if not org_bounds:
        return []
    rows = frappe.db.sql(
        """
        SELECT name
        FROM `tabOrganization`
        WHERE lft >= %(lft)s AND rgt <= %(rgt)s
        ORDER BY lft ASC, name ASC
        """,
        {"lft": org_bounds.lft, "rgt": org_bounds.rgt},
        as_list=True,
    )
    return [r[0] for r in rows]


def _apply_user_scope_conditions(user: str, conds: list, params: dict, alias: str = "i") -> None:
    """Apply the staff user's institutional Inquiry visibility scope before aggregation."""
    scope = get_admissions_file_staff_scope(user)
    if not scope.get("allowed"):
        conds.append("1=0")
        return

    if scope.get("bypass"):
        return

    roles = set(frappe.get_roles(user))
    org_scope = _clean_values(scope.get("org_scope") or [])
    school_scope = _clean_values(scope.get("school_scope") or [])

    visibility_clauses = [f"{alias}.assigned_to = %(visible_user)s"]
    params["visible_user"] = user

    if school_scope:
        visibility_clauses.append(f"{alias}.school IN %(user_school_scope)s")
        params["user_school_scope"] = tuple(school_scope)
    elif org_scope:
        visibility_clauses.append(f"{alias}.organization IN %(user_org_scope)s")
        params["user_org_scope"] = tuple(org_scope)

        org_schools = _clean_values(get_schools_for_organization_scope(org_scope))
        if org_schools:
            visibility_clauses.append(f"{alias}.school IN %(user_org_school_scope)s")
            params["user_org_school_scope"] = tuple(org_schools)

    if "Admission Manager" in roles and org_scope:
        visibility_clauses.append(f"((IFNULL({alias}.organization, '') = '') AND (IFNULL({alias}.school, '') = ''))")

    conds.append("(" + " OR ".join(visibility_clauses) + ")")


def _apply_org_school_conditions(filters: dict, conds: list, params: dict):
    org_filter = filters.get("organization")
    if org_filter:
        orgs = _get_descendant_organizations(org_filter)
        if orgs:
            conds.append("i.organization IN %(organizations)s")
            params["organizations"] = tuple(orgs)
        else:
            conds.append("1=0")

    school_filter = filters.get("school")
    if school_filter:
        schools = get_descendant_schools(school_filter)
        if schools:
            conds.append("i.school IN %(schools)s")
            params["schools"] = tuple(schools)
        else:
            conds.append("1=0")


def _apply_common_conditions(filters: dict, site_tz: str, user: str | None = None):
    conds = []
    params = {}
    fd, td = _resolve_window(filters)
    conds.append(f"{SUBMITTED_LOCAL_EXPR} >= %(from)s AND {SUBMITTED_LOCAL_EXPR} <= %(to)s")
    params.update(
        {
            "from": f"{fd} 00:00:00",
            "to": f"{td} 23:59:59",
            "site_tz": site_tz,
        }
    )

    if user:
        _apply_user_scope_conditions(user, conds, params)

    _apply_org_school_conditions(filters, conds, params)

    if filters.get("type_of_inquiry"):
        conds.append("i.type_of_inquiry = %(type)s")
        params["type"] = filters["type_of_inquiry"]

    if filters.get("source"):
        conds.append("i.source = %(source)s")
        params["source"] = filters["source"]

    if filters.get("assigned_to"):
        conds.append("i.assigned_to = %(assignee)s")
        params["assignee"] = filters["assigned_to"]

    if filters.get("sla_status"):
        conds.append("i.sla_status = %(sla)s")
        params["sla"] = filters["sla_status"]

    lane = (filters.get("assignment_lane") or "").strip()
    if lane:
        if lane not in ("Admission", "Staff"):
            frappe.throw("Invalid assignment_lane filter.")
        conds.append("COALESCE(i.assignment_lane, 'Admission') = %(assignment_lane)s")
        params["assignment_lane"] = lane

    return " AND ".join(conds), params


def _rest_conditions(filters: dict, user: str | None = None):
    conds, params = [], {}
    if user:
        _apply_user_scope_conditions(user, conds, params)
    _apply_org_school_conditions(filters, conds, params)
    if filters.get("type_of_inquiry"):
        conds.append("i.type_of_inquiry = %(type)s")
        params["type"] = filters["type_of_inquiry"]
    if filters.get("source"):
        conds.append("i.source = %(source)s")
        params["source"] = filters["source"]
    if filters.get("assigned_to"):
        conds.append("i.assigned_to = %(assignee)s")
        params["assignee"] = filters["assigned_to"]
    if filters.get("sla_status"):
        conds.append("i.sla_status = %(sla)s")
        params["sla"] = filters["sla_status"]
    lane = (filters.get("assignment_lane") or "").strip()
    if lane:
        if lane not in ("Admission", "Staff"):
            frappe.throw("Invalid assignment_lane filter.")
        conds.append("COALESCE(i.assignment_lane, 'Admission') = %(assignment_lane)s")
        params["assignment_lane"] = lane
    return " AND ".join(conds) or "1=1", params


@frappe.whitelist()
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


ZERO_LOST_LEAD_VIEWS = [
    {
        "id": "unassigned_new",
        "title": _("Unassigned new inquiries"),
        "tone": "danger",
        "condition": "COALESCE(i.workflow_state, 'New') = 'New' AND IFNULL(i.assigned_to, '') = ''",
        "next_action": _("Assign owner"),
    },
    {
        "id": "uncontacted_due_today",
        "title": _("Uncontacted and due today"),
        "tone": "warning",
        "condition": (
            "COALESCE(i.workflow_state, 'New') NOT IN ('Contacted', 'Qualified', 'Archived') "
            "AND i.first_contacted_at IS NULL "
            "AND i.first_contact_due_on IS NOT NULL "
            "AND i.first_contact_due_on = %(today)s"
        ),
        "next_action": _("Record first contact"),
    },
    {
        "id": "overdue_first_contact",
        "title": _("Overdue first contact"),
        "tone": "danger",
        "condition": (
            "COALESCE(i.workflow_state, 'New') NOT IN ('Contacted', 'Qualified', 'Archived') "
            "AND i.first_contacted_at IS NULL "
            "AND i.first_contact_due_on IS NOT NULL "
            "AND i.first_contact_due_on < %(today)s"
        ),
        "next_action": _("Record first contact"),
    },
    {
        "id": "contacted_no_followup",
        "title": _("Contacted but no follow-up date"),
        "tone": "warning",
        "condition": (
            "COALESCE(i.workflow_state, 'New') = 'Contacted' "
            "AND IFNULL(i.followup_due_on, '') = '' "
            "AND IFNULL(i.student_applicant, '') = ''"
        ),
        "next_action": _("Set next action, qualify, or archive"),
    },
    {
        "id": "qualified_not_invited",
        "title": _("Qualified but not invited to apply"),
        "tone": "info",
        "condition": "COALESCE(i.workflow_state, 'New') = 'Qualified' AND IFNULL(i.student_applicant, '') = ''",
        "next_action": _("Invite to apply"),
    },
    {
        "id": "invited_no_progress",
        "title": _("Invited but no applicant progress"),
        "tone": "info",
        "condition": (
            "IFNULL(i.student_applicant, '') != '' "
            "AND sa.name IS NOT NULL "
            "AND sa.application_status = 'Invited' "
            "AND sa.submitted_at IS NULL"
        ),
        "next_action": _("Open applicant"),
    },
    {
        "id": "archived_without_reason",
        "title": _("Archived without reason"),
        "tone": "danger",
        "condition": "COALESCE(i.workflow_state, 'New') = 'Archived' AND IFNULL(i.archive_reason, '') = ''",
        "next_action": _("Add archive reason"),
    },
    {
        "id": "stale_unowned",
        "title": _("Leads older than 24 hours with no owner"),
        "tone": "danger",
        "condition": (
            "COALESCE(i.workflow_state, 'New') != 'Archived' "
            "AND IFNULL(i.assigned_to, '') = '' "
            "AND COALESCE(i.submitted_at, i.creation) < %(stale_before)s"
        ),
        "next_action": _("Assign owner"),
    },
]


def _zero_lost_view_by_id(view_id: str | None) -> dict:
    requested = (view_id or "").strip()
    for view in ZERO_LOST_LEAD_VIEWS:
        if view["id"] == requested:
            return view
    return ZERO_LOST_LEAD_VIEWS[0]


def _to_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _desk_route_slug(doctype: str) -> str:
    return frappe.scrub(doctype).replace("_", "-")


def _doc_url(doctype: str, name: str | None) -> str | None:
    resolved_name = (name or "").strip()
    if not resolved_name:
        return None
    return f"/desk/{_desk_route_slug(doctype)}/{quote(resolved_name, safe='')}"


def _lead_title(row: dict) -> str:
    parts = [(row.get("first_name") or "").strip(), (row.get("last_name") or "").strip()]
    title = " ".join(part for part in parts if part).strip()
    return title or (row.get("name") or "")


def _stringify_dt(value):
    return str(value) if value else None


def _age_hours(value, now_value) -> float | None:
    if not value:
        return None
    try:
        return round((get_datetime(now_value) - get_datetime(value)).total_seconds() / 3600.0, 1)
    except Exception:
        return None


def _zero_lost_row_payload(row: dict, *, active_view: dict, now_value) -> dict:
    inquiry_name = (row.get("name") or "").strip()
    applicant_name = (row.get("student_applicant") or "").strip()
    return {
        "name": inquiry_name,
        "lead_title": _lead_title(row),
        "email": row.get("email"),
        "phone_number": row.get("phone_number"),
        "type_of_inquiry": row.get("type_of_inquiry"),
        "source": row.get("source"),
        "organization": row.get("organization"),
        "school": row.get("school"),
        "workflow_state": row.get("workflow_state") or "New",
        "sla_status": row.get("sla_status"),
        "assigned_to": row.get("assigned_to"),
        "assignment_lane": row.get("assignment_lane") or "Admission",
        "student_applicant": applicant_name or None,
        "student_applicant_status": row.get("student_applicant_status"),
        "submitted_at": _stringify_dt(row.get("submitted_at")),
        "first_contact_due_on": _stringify_dt(row.get("first_contact_due_on")),
        "followup_due_on": _stringify_dt(row.get("followup_due_on")),
        "first_contacted_at": _stringify_dt(row.get("first_contacted_at")),
        "applicant_submitted_at": _stringify_dt(row.get("applicant_submitted_at")),
        "archive_reason": row.get("archive_reason"),
        "next_action_note": row.get("next_action_note"),
        "age_hours": _age_hours(row.get("submitted_at") or row.get("creation"), now_value),
        "open_url": _doc_url("Inquiry", inquiry_name),
        "student_applicant_url": _doc_url("Student Applicant", applicant_name),
        "next_action": {
            "label": active_view.get("next_action"),
            "target_url": _doc_url("Student Applicant", applicant_name)
            if active_view.get("id") == "invited_no_progress" and applicant_name
            else _doc_url("Inquiry", inquiry_name),
        },
    }


def _zero_lost_params() -> dict:
    now_value = now_datetime()
    return {
        "today": nowdate(),
        "stale_before": now_value - timedelta(hours=24),
        "now": now_value,
    }


def _build_zero_lost_lead_payload(filters: dict, *, user: str, active_view: str | None, start=0, limit=25) -> dict:
    base_where, base_params = _rest_conditions(filters, user=user)
    active = _zero_lost_view_by_id(active_view)

    start_value = max(_to_int(start, 0), 0)
    limit_value = _to_int(limit, 25)
    if limit_value < 1:
        limit_value = 25
    if limit_value > 100:
        limit_value = 100

    runtime_params = _zero_lost_params()
    count_params = {**base_params, **runtime_params}

    views = []
    active_total = 0
    for view in ZERO_LOST_LEAD_VIEWS:
        total = frappe.db.sql(
            """
            SELECT COUNT(*)
            FROM `tabInquiry` i
            LEFT JOIN `tabStudent Applicant` sa ON sa.name = i.student_applicant
            WHERE ({base_where}) AND ({view_condition})
            """.format(base_where=base_where, view_condition=view["condition"]),
            count_params,
            as_dict=False,
        )[0][0]
        total = int(total or 0)
        if view["id"] == active["id"]:
            active_total = total
        views.append(
            {
                "id": view["id"],
                "title": view["title"],
                "tone": view["tone"],
                "count": total,
                "next_action": view["next_action"],
            }
        )

    row_params = {**count_params, "start": start_value, "limit": limit_value}
    rows = frappe.db.sql(
        """
        SELECT
            i.name,
            i.creation,
            i.first_name,
            i.last_name,
            i.email,
            i.phone_number,
            i.type_of_inquiry,
            i.source,
            i.organization,
            i.school,
            i.workflow_state,
            i.sla_status,
            i.assigned_to,
            i.assignment_lane,
            i.student_applicant,
            i.submitted_at,
            i.first_contact_due_on,
            i.followup_due_on,
            i.first_contacted_at,
            i.archive_reason,
            i.next_action_note,
            sa.application_status AS student_applicant_status,
            sa.submitted_at AS applicant_submitted_at
        FROM `tabInquiry` i
        LEFT JOIN `tabStudent Applicant` sa ON sa.name = i.student_applicant
        WHERE ({base_where}) AND ({view_condition})
        ORDER BY
            COALESCE(i.first_contact_due_on, DATE(i.submitted_at), DATE(i.creation)) ASC,
            COALESCE(i.submitted_at, i.creation) ASC,
            i.modified DESC
        LIMIT %(start)s, %(limit)s
        """.format(base_where=base_where, view_condition=active["condition"]),
        row_params,
        as_dict=True,
    )

    return {
        "views": views,
        "active_view": active["id"],
        "rows": [_zero_lost_row_payload(row, active_view=active, now_value=runtime_params["now"]) for row in rows],
        "pagination": {
            "start": start_value,
            "limit": limit_value,
            "total": active_total,
            "has_next": start_value + limit_value < active_total,
        },
        "generated_at": _stringify_dt(runtime_params["now"]),
        "scope": {
            "operational_date_mode": "all_time",
        },
    }


@frappe.whitelist()
def get_zero_lost_lead_context(filters=None, active_view: str | None = None, start=0, limit=25):
    user = _ensure_access()
    parsed_filters = frappe.parse_json(filters) or {}
    return {
        "command_center": _build_zero_lost_lead_payload(
            parsed_filters,
            user=user,
            active_view=active_view,
            start=start,
            limit=limit,
        ),
        "analytics": _build_dashboard_data(parsed_filters, user=user),
    }


@frappe.whitelist()
def get_inquiry_organizations():
    user = _ensure_access()
    scope = get_admissions_file_staff_scope(user)
    if not scope.get("allowed"):
        return []
    if not scope.get("bypass"):
        org_scope = _clean_values(scope.get("org_scope") or [])
        if not org_scope:
            return []
        rows = frappe.db.sql(
            """
            SELECT name
            FROM `tabOrganization`
            WHERE name IN %(organizations)s
            ORDER BY lft ASC, name ASC
            """,
            {"organizations": tuple(org_scope)},
            as_list=True,
        )
        return [r[0] for r in rows]

    rows = frappe.db.sql(
        """
        SELECT name
        FROM `tabOrganization`
        ORDER BY lft ASC, name ASC
        """,
        as_list=True,
    )
    return [r[0] for r in rows]


@frappe.whitelist()
def get_inquiry_schools():
    user = _ensure_access()
    scope = get_admissions_file_staff_scope(user)
    if not scope.get("allowed"):
        return []
    if not scope.get("bypass"):
        school_scope = _clean_values(scope.get("school_scope") or [])
        if not school_scope:
            org_scope = _clean_values(scope.get("org_scope") or [])
            school_scope = _clean_values(get_schools_for_organization_scope(org_scope)) if org_scope else []
        if not school_scope:
            return []
        rows = frappe.db.sql(
            """
            SELECT name
            FROM `tabSchool`
            WHERE name IN %(schools)s
            ORDER BY lft ASC, name ASC
            """,
            {"schools": tuple(school_scope)},
            as_list=True,
        )
        return [r[0] for r in rows]

    rows = frappe.db.sql(
        """
        SELECT name
        FROM `tabSchool`
        ORDER BY lft ASC, name ASC
        """,
        as_list=True,
    )
    return [r[0] for r in rows]


@frappe.whitelist()
def academic_year_link_query(doctype=None, txt=None, searchfield=None, start=0, page_len=20, filters=None):
    return frappe.db.sql(
        """
        SELECT name
        FROM `tabAcademic Year`
        WHERE name LIKE %(txt)s
        ORDER BY year_start_date DESC, name DESC
        LIMIT %(start)s, %(page_len)s
        """,
        {"txt": f"%{txt or ''}%", "start": int(start or 0), "page_len": int(page_len or 20)},
    )


@frappe.whitelist(allow_guest=True)
@frappe.validate_and_sanitize_search_inputs
def inquiry_organization_link_query(doctype=None, txt=None, searchfield=None, start=0, page_len=20, filters=None):
    return frappe.db.sql(
        """
        SELECT name
        FROM `tabOrganization`
        WHERE name LIKE %(txt)s
            AND get_inquiry = 1
            AND COALESCE(archived, 0) = 0
        ORDER BY lft ASC, name ASC
        LIMIT %(start)s, %(page_len)s
        """,
        {"txt": f"%{txt or ''}%", "start": int(start or 0), "page_len": int(page_len or 20)},
    )


@frappe.whitelist(allow_guest=True)
@frappe.validate_and_sanitize_search_inputs
def inquiry_school_link_query(doctype=None, txt=None, searchfield=None, start=0, page_len=20, filters=None):
    filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
    organization = (filters.get("organization") or "").strip()
    params = {
        "txt": f"%{txt or ''}%",
        "start": int(start or 0),
        "page_len": int(page_len or 20),
    }
    where = [
        "COALESCE(s.show_in_inquiry, 0) = 1",
        "COALESCE(o.get_inquiry, 0) = 1",
        "COALESCE(o.archived, 0) = 0",
        "(s.name LIKE %(txt)s OR s.school_name LIKE %(txt)s)",
    ]

    if organization:
        organization_scope = _get_descendant_organizations(organization)
        if not organization_scope:
            return []
        where.append("s.organization IN %(organizations)s")
        params["organizations"] = tuple(organization_scope)

    return frappe.db.sql(
        f"""
        SELECT
            s.name,
            COALESCE(NULLIF(s.school_name, ''), s.name) AS school_name
        FROM `tabSchool` s
        INNER JOIN `tabOrganization` o ON o.name = s.organization
        WHERE {" AND ".join(where)}
        ORDER BY s.lft ASC, s.school_name ASC, s.name ASC
        LIMIT %(start)s, %(page_len)s
        """,
        params,
    )


@frappe.whitelist(allow_guest=True)
def get_inquiry_acknowledgement_context(organization=None, school=None, type_of_inquiry=None):
    from ifitwala_ed.admission.inquiry_acknowledgement import build_public_acknowledgement_context

    return build_public_acknowledgement_context(
        organization=organization,
        school=school,
        type_of_inquiry=type_of_inquiry,
    )


@frappe.whitelist()
def admission_user_link_query(doctype=None, txt=None, searchfield=None, start=0, page_len=20, filters=None):
    """Enabled users linked to active Employee rows; match name/full_name/email."""
    filters = filters or {}
    organization = (filters.get("organization") or "").strip()
    school = (filters.get("school") or "").strip()

    org_scope = _get_descendant_organizations(organization) if organization else []
    if organization and not org_scope:
        return []
    school_scope = get_descendant_schools(school) if school else []
    if school and not school_scope:
        return []

    where = ["ifnull(e.employment_status, '') = 'Active'", "ifnull(e.user_id, '') <> ''"]
    params = {
        "txt": f"%{txt or ''}%",
        "start": int(start or 0),
        "page_len": int(page_len or 20),
    }
    if org_scope:
        where.append("e.organization IN %(org_scope)s")
        params["org_scope"] = tuple(org_scope)
    if school_scope:
        where.append("e.school IN %(school_scope)s")
        params["school_scope"] = tuple(school_scope)

    return frappe.db.sql(
        f"""
        SELECT
            u.name,
            COALESCE(NULLIF(u.full_name, ''), NULLIF(e.employee_full_name, ''), u.name) as full_name
        FROM `tabUser` u
        JOIN `tabEmployee` e ON e.user_id = u.name
        WHERE u.enabled = 1
            AND {" AND ".join(where)}
            AND (
            u.name LIKE %(txt)s
            OR u.full_name LIKE %(txt)s
            OR e.employee_full_name LIKE %(txt)s
            OR u.email LIKE %(txt)s
            )
        ORDER BY full_name ASC, u.creation DESC
        LIMIT %(start)s, %(page_len)s
        """,
        params,
    )


@frappe.whitelist()
def get_inquiry_types():
    # Returns a simple list of distinct, non-empty types (alphabetical)
    rows = frappe.db.sql(
        """
        SELECT DISTINCT type_of_inquiry
        FROM `tabInquiry`
        WHERE COALESCE(type_of_inquiry, '') <> ''
        ORDER BY type_of_inquiry
        """,
        as_dict=False,
    )
    return [r[0] for r in rows]


@frappe.whitelist()
def get_inquiry_sources():
    _ensure_access()
    meta = frappe.get_meta("Inquiry")
    source_field = meta.get_field("source")
    if not source_field:
        return []

    options = [option.strip() for option in (source_field.options or "").splitlines() if option.strip()]
    return options
