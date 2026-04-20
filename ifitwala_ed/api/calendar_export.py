from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import frappe
import pytz
from frappe import _
from frappe.utils import add_to_date, format_date, get_datetime, get_url, now_datetime

from ifitwala_ed.api import calendar_staff_feed
from ifitwala_ed.api.calendar_core import _resolve_employee_for_user, _system_tzinfo

TEMPLATE_PATH = "ifitwala_ed/templates/print/staff_timetable_export.html"
CSS_PATH = Path(__file__).resolve().parents[1] / "templates" / "print" / "staff_timetable_export.css"
PDF_OPTIONS = {
    "page-size": "A4",
    "orientation": "Landscape",
    "margin-top": "9mm",
    "margin-right": "10mm",
    "margin-bottom": "9mm",
    "margin-left": "10mm",
}

DEFAULT_EXPORT_SOURCES = ("student_group", "meeting", "school_event", "staff_holiday")
DEFAULT_EXPORT_PRESET = "this_week"
VALID_EXPORT_PRESETS = {DEFAULT_EXPORT_PRESET, "next_2_weeks", "next_month"}

SOURCE_LABELS = {
    "student_group": _("Class"),
    "meeting": _("Meeting"),
    "school_event": _("School Event"),
    "staff_holiday": _("Holiday"),
}

SOURCE_CLASSES = {
    "student_group": "class",
    "meeting": "meeting",
    "school_event": "school",
    "staff_holiday": "holiday",
}

SOURCE_SORT = {
    "staff_holiday": 0,
    "school_event": 1,
    "meeting": 2,
    "student_group": 3,
}


def export_staff_timetable_pdf(preset: str | None = None):
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Please sign in to view your calendar."), frappe.PermissionError)

    tzinfo = _system_tzinfo()
    local_now = _localize_datetime(now_datetime(), tzinfo)
    window = _resolve_staff_timetable_window(preset, local_now.date())

    employee = _resolve_employee_for_user(
        user,
        fields=[
            "name",
            "employee_full_name",
            "designation",
            "employee_group",
            "school",
            "organization",
        ],
        employment_status_filter=["!=", "Inactive"],
    )

    payload = calendar_staff_feed.get_staff_calendar(
        from_datetime=_combine(window["start_date"], time.min, tzinfo).isoformat(),
        to_datetime=_combine(window["end_date_exclusive"], time.min, tzinfo).isoformat(),
        sources=list(DEFAULT_EXPORT_SOURCES),
        force_refresh=False,
    )

    context = _build_staff_timetable_context(
        user=user,
        employee=employee,
        payload=payload,
        window=window,
        tzinfo=tzinfo,
        generated_at=local_now,
    )
    html = _render_staff_timetable_export_html(context)
    pdf_content = _render_staff_timetable_pdf(html)

    frappe.local.response["type"] = "download"
    frappe.local.response["filename"] = _build_export_filename(window)
    frappe.local.response["filecontent"] = pdf_content
    frappe.local.response["display_content_as"] = "inline"
    frappe.local.response["content_type"] = "application/pdf"


def _build_export_filename(window: dict[str, Any]) -> str:
    start_key = window["start_date"].isoformat()
    return f"staff-timetable-{window['preset']}-{start_key}.pdf"


def _render_staff_timetable_pdf(html: str) -> bytes:
    from frappe.utils.pdf import get_pdf

    return get_pdf(html, options=PDF_OPTIONS)


def _render_staff_timetable_export_html(context: dict[str, Any]) -> str:
    return frappe.render_template(TEMPLATE_PATH, context)


def _build_staff_timetable_context(
    *,
    user: str,
    employee: dict[str, Any] | None,
    payload: dict[str, Any],
    window: dict[str, Any],
    tzinfo: pytz.BaseTzInfo,
    generated_at: datetime,
) -> dict[str, Any]:
    events = payload.get("events") or []
    brand = _resolve_brand_context(employee=employee, events=events)
    weeks = _build_timetable_weeks(
        events=events,
        start_date=window["start_date"],
        end_date_exclusive=window["end_date_exclusive"],
        tzinfo=tzinfo,
    )
    count_cards = _build_count_cards(payload.get("counts") or {})

    return {
        "css": CSS_PATH.read_text(encoding="utf-8"),
        "brand": brand,
        "employee_name": (
            (employee or {}).get("employee_full_name") or frappe.db.get_value("User", user, "full_name") or user
        ),
        "designation": (employee or {}).get("designation") or "",
        "employee_group": (employee or {}).get("employee_group") or "",
        "preset_label": window["preset_label"],
        "range_label": window["range_label"],
        "generated_on": generated_at.strftime("%d %b %Y %H:%M"),
        "week_count": len(weeks),
        "count_cards": count_cards,
        "weeks": weeks,
        "has_events": any(week.get("event_count") for week in weeks),
    }


def _build_count_cards(counts: dict[str, Any]) -> list[dict[str, Any]]:
    cards = []
    for source in DEFAULT_EXPORT_SOURCES:
        cards.append(
            {
                "label": SOURCE_LABELS[source],
                "value": int(counts.get(source) or 0),
                "source_class": SOURCE_CLASSES[source],
            }
        )
    return cards


def _resolve_brand_context(*, employee: dict[str, Any] | None, events: list[dict[str, Any]]) -> dict[str, str]:
    school_name = ((employee or {}).get("school") or "").strip()
    organization_name = ((employee or {}).get("organization") or "").strip()

    if not school_name:
        school_name = _infer_school_from_events(events)

    school_meta = (
        frappe.db.get_value(
            "School",
            school_name,
            ["school_name", "school_logo", "school_tagline", "organization"],
            as_dict=True,
        )
        if school_name
        else None
    )
    if school_meta and school_meta.get("organization"):
        organization_name = (school_meta.get("organization") or "").strip()

    org_meta = (
        frappe.db.get_value(
            "Organization",
            organization_name,
            ["organization_name", "organization_logo"],
            as_dict=True,
        )
        if organization_name and organization_name != "All Organizations"
        else None
    )

    brand_name = (school_meta or {}).get("school_name") or (org_meta or {}).get("organization_name") or "Ifitwala Ed"
    secondary_brand = ""
    if (
        org_meta
        and (org_meta.get("organization_name") or "").strip()
        and org_meta.get("organization_name") != brand_name
    ):
        secondary_brand = (org_meta.get("organization_name") or "").strip()

    return {
        "brand_name": brand_name,
        "secondary_brand": secondary_brand,
        "tagline": ((school_meta or {}).get("school_tagline") or "").strip(),
        "logo_url": _absolute_media_url((school_meta or {}).get("school_logo"))
        or _absolute_media_url((org_meta or {}).get("organization_logo"))
        or "",
        "school_label": (school_meta or {}).get("school_name") or school_name or "",
        "organization_label": (org_meta or {}).get("organization_name") or organization_name or "",
    }


def _infer_school_from_events(events: list[dict[str, Any]]) -> str:
    for event in events:
        meta = event.get("meta") or {}
        school_name = (meta.get("school") or meta.get("calendar_school") or "").strip()
        if school_name:
            return school_name
    return ""


def _absolute_media_url(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    if raw.startswith(("http://", "https://", "data:")):
        return raw
    return get_url(raw)


def _resolve_staff_timetable_window(preset: str | None, anchor_date: date) -> dict[str, Any]:
    preset_key = _normalize_export_preset(preset)

    if preset_key == DEFAULT_EXPORT_PRESET:
        start_date = _start_of_week(anchor_date)
        end_date_exclusive = start_date + timedelta(days=7)
        preset_label = _("This Week")
    elif preset_key == "next_2_weeks":
        start_date = _start_of_week(anchor_date)
        end_date_exclusive = start_date + timedelta(days=14)
        preset_label = _("Next 2 Weeks")
    else:
        next_month_start = get_datetime(add_to_date(anchor_date.replace(day=1), months=1, as_datetime=False)).date()
        next_month_end = get_datetime(add_to_date(next_month_start, months=1, as_datetime=False)).date()
        start_date = next_month_start
        end_date_exclusive = next_month_end
        preset_label = _("Next Month")

    return {
        "preset": preset_key,
        "preset_label": preset_label,
        "start_date": start_date,
        "end_date_exclusive": end_date_exclusive,
        "range_label": _format_date_span(start_date, end_date_exclusive - timedelta(days=1)),
    }


def _normalize_export_preset(value: str | None) -> str:
    preset = (value or DEFAULT_EXPORT_PRESET).strip()
    if preset not in VALID_EXPORT_PRESETS:
        frappe.throw(_("Unsupported timetable export preset."), frappe.ValidationError)
    return preset


def _start_of_week(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _format_date_span(start_date: date, end_date: date) -> str:
    return _("{start} to {end}").format(
        start=format_date(start_date),
        end=format_date(end_date),
    )


def _build_timetable_weeks(
    *,
    events: list[dict[str, Any]],
    start_date: date,
    end_date_exclusive: date,
    tzinfo: pytz.BaseTzInfo,
) -> list[dict[str, Any]]:
    all_day_by_date: dict[date, list[dict[str, Any]]] = defaultdict(list)
    timed_by_date: dict[date, list[dict[str, Any]]] = defaultdict(list)

    for event in events:
        _append_event_to_day_buckets(
            event=event,
            all_day_by_date=all_day_by_date,
            timed_by_date=timed_by_date,
            start_date=start_date,
            end_date_exclusive=end_date_exclusive,
            tzinfo=tzinfo,
        )

    first_week_start = _start_of_week(start_date)
    last_week_start = _start_of_week(end_date_exclusive - timedelta(days=1))

    weeks = []
    current_week_start = first_week_start
    total_pages = ((last_week_start - first_week_start).days // 7) + 1
    page_number = 1
    while current_week_start <= last_week_start:
        week_days = []
        event_count = 0
        week_range_end = current_week_start + timedelta(days=6)
        for offset in range(7):
            current_day = current_week_start + timedelta(days=offset)
            all_day_events = sorted(
                all_day_by_date.get(current_day, []),
                key=lambda item: (item["source_sort"], item["title"], item["time_sort"]),
            )
            timed_events = sorted(
                timed_by_date.get(current_day, []),
                key=lambda item: (item["time_sort"], item["source_sort"], item["title"]),
            )
            event_count += len(all_day_events) + len(timed_events)
            week_days.append(
                {
                    "iso": current_day.isoformat(),
                    "weekday_short": current_day.strftime("%a"),
                    "weekday_long": current_day.strftime("%A"),
                    "date_label": current_day.strftime("%d %b"),
                    "is_weekend": offset >= 5,
                    "in_window": start_date <= current_day < end_date_exclusive,
                    "all_day_events": all_day_events,
                    "timed_events": timed_events,
                }
            )

        weeks.append(
            {
                "page_number": page_number,
                "total_pages": total_pages,
                "page_label": _("Week {0} of {1}").format(page_number, total_pages),
                "range_label": _format_date_span(current_week_start, week_range_end),
                "days": week_days,
                "event_count": event_count,
            }
        )
        page_number += 1
        current_week_start += timedelta(days=7)

    return weeks


def _append_event_to_day_buckets(
    *,
    event: dict[str, Any],
    all_day_by_date: dict[date, list[dict[str, Any]]],
    timed_by_date: dict[date, list[dict[str, Any]]],
    start_date: date,
    end_date_exclusive: date,
    tzinfo: pytz.BaseTzInfo,
):
    start_dt = _coerce_export_datetime(event.get("start"), tzinfo)
    end_dt = _coerce_export_datetime(event.get("end"), tzinfo)
    if not start_dt:
        return
    if not end_dt or end_dt <= start_dt:
        end_dt = start_dt + timedelta(minutes=45)

    source = (event.get("source") or "").strip() or "school_event"
    source_label = SOURCE_LABELS.get(source, _("Commitment"))
    source_class = SOURCE_CLASSES.get(source, "generic")
    event_color = (event.get("color") or "").strip() or "#64748B"
    meta = event.get("meta") or {}

    if bool(event.get("allDay")):
        current_day = start_dt.date()
        end_day_exclusive = end_dt.date()
        while current_day < end_day_exclusive:
            if start_date <= current_day < end_date_exclusive:
                all_day_by_date[current_day].append(
                    {
                        "title": event.get("title") or source_label,
                        "source_label": source_label,
                        "source_class": source_class,
                        "source_sort": SOURCE_SORT.get(source, 99),
                        "color": event_color,
                        "location": (meta.get("location") or "").strip(),
                        "time_sort": 0,
                    }
                )
            current_day += timedelta(days=1)
        return

    segment_day = start_dt.date()
    last_day = end_dt.date()
    while segment_day <= last_day:
        day_start = _combine(segment_day, time.min, tzinfo)
        next_day = day_start + timedelta(days=1)
        segment_start = max(start_dt, day_start)
        segment_end = min(end_dt, next_day)
        if segment_end > segment_start and start_date <= segment_day < end_date_exclusive:
            timed_by_date[segment_day].append(
                {
                    "title": event.get("title") or source_label,
                    "source_label": source_label,
                    "source_class": source_class,
                    "source_sort": SOURCE_SORT.get(source, 99),
                    "color": event_color,
                    "location": (meta.get("location") or "").strip(),
                    "time_label": _format_time_range(segment_start, segment_end),
                    "time_sort": (segment_start.hour * 60) + segment_start.minute,
                }
            )
        segment_day += timedelta(days=1)


def _coerce_export_datetime(value: str | None, tzinfo: pytz.BaseTzInfo) -> datetime | None:
    if not value:
        return None
    parsed = get_datetime(value)
    if parsed.tzinfo:
        return parsed.astimezone(tzinfo)
    return tzinfo.localize(parsed)


def _combine(day: date, clock: time, tzinfo: pytz.BaseTzInfo) -> datetime:
    return tzinfo.localize(datetime.combine(day, clock))


def _localize_datetime(dt: datetime, tzinfo: pytz.BaseTzInfo) -> datetime:
    if dt.tzinfo:
        return dt.astimezone(tzinfo)
    return tzinfo.localize(dt)


def _format_time_range(start_dt: datetime, end_dt: datetime) -> str:
    return f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
