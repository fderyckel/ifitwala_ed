# ifitwala_ed/website/providers/academic_calendar.py

from __future__ import annotations

import frappe
from frappe.utils import getdate, nowdate
from frappe.utils.caching import redis_cache

DEFAULT_TITLE = "Academic Calendar"


def _normalize_limit(value) -> int:
    try:
        return max(int(value or 6), 1)
    except (TypeError, ValueError):
        return 6


def _pick_calendar_for_school(school_name: str):
    calendars = frappe.get_all(
        "School Calendar",
        filters={"school": school_name},
        fields=["name", "academic_year", "modified"],
        order_by="modified desc",
        limit=20,
    )
    if not calendars:
        return None

    academic_year_names = [row.get("academic_year") for row in calendars if row.get("academic_year")]
    year_map = {
        row["name"]: row
        for row in frappe.get_all(
            "Academic Year",
            filters={"name": ["in", academic_year_names]},
            fields=["name", "academic_year_name", "year_start_date", "year_end_date"],
            limit=max(len(academic_year_names), 20),
        )
    }
    today = getdate(nowdate())

    active = []
    upcoming = []
    past = []
    for row in calendars:
        year = year_map.get(row.get("academic_year"))
        if not year:
            past.append((row, year))
            continue
        start = getdate(year.get("year_start_date"))
        end = getdate(year.get("year_end_date"))
        if start <= today <= end:
            active.append((row, year))
        elif today < start:
            upcoming.append((row, year))
        else:
            past.append((row, year))

    if active:
        return active[0]
    if upcoming:
        upcoming.sort(key=lambda item: getdate(item[1].get("year_start_date")))
        return upcoming[0]
    return past[0]


@redis_cache(ttl=1800)
def _get_calendar_payload(
    school_name: str, include_terms: bool, include_holidays: bool, limit: int
) -> dict[str, object]:
    picked = _pick_calendar_for_school(school_name)
    if not picked:
        return {
            "calendar_label": None,
            "items": [],
            "has_items": False,
        }

    calendar_row, academic_year = picked
    calendar = frappe.get_doc("School Calendar", calendar_row.get("name"))
    today = getdate(nowdate())
    items = []

    if include_terms:
        for row in calendar.terms or []:
            start = getdate(row.start) if row.start else None
            if start and start >= today:
                items.append(
                    {
                        "kind": "term",
                        "title": row.term,
                        "date_text": f"{row.start} to {row.end}" if row.end else str(row.start),
                        "sort_date": start,
                    }
                )

    if include_holidays:
        for row in calendar.holidays or []:
            holiday_date = getdate(row.holiday_date) if row.holiday_date else None
            if holiday_date and holiday_date >= today:
                items.append(
                    {
                        "kind": "holiday",
                        "title": row.description or "School Holiday",
                        "date_text": str(row.holiday_date),
                        "sort_date": holiday_date,
                    }
                )

    items.sort(key=lambda item: item["sort_date"])
    items = [{key: value for key, value in item.items() if key != "sort_date"} for item in items[:limit]]
    return {
        "calendar_label": (academic_year.get("academic_year_name") if academic_year else None) or calendar.name,
        "items": items,
        "has_items": bool(items),
    }


def invalidate_academic_calendar_cache(*_args, **_kwargs):
    clear_cache = getattr(_get_calendar_payload, "clear_cache", None)
    if callable(clear_cache):
        clear_cache()


def get_context(*, school, page, block_props):
    include_terms = bool(block_props.get("include_terms", True))
    include_holidays = bool(block_props.get("include_holidays", True))
    limit = _normalize_limit(block_props.get("limit"))
    payload = _get_calendar_payload(
        school_name=school.name,
        include_terms=include_terms,
        include_holidays=include_holidays,
        limit=limit,
    )

    return {
        "data": {
            "title": (block_props.get("title") or "").strip() or DEFAULT_TITLE,
            "description": (block_props.get("description") or "").strip() or None,
            "calendar_label": payload["calendar_label"],
            "items": payload["items"],
            "has_items": payload["has_items"],
        }
    }
