# ifitwala_ed/api/calendar_subscription.py

from __future__ import annotations

import hashlib
from datetime import datetime, time, timedelta, timezone
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

from ifitwala_ed.api import calendar_staff_feed
from ifitwala_ed.api.calendar_core import (
    _localize_datetime,
    _resolve_employee_for_user,
    _system_tzinfo,
)

CALENDAR_SUBSCRIPTION_DOCTYPE = "Calendar Subscription Token"
STAFF_FEED_TYPE = "staff_calendar"
STAFF_SUBJECT_TYPE = "Staff"
STAFF_SUBSCRIPTION_SOURCES = ("student_group", "meeting", "school_event", "staff_holiday")
TOKEN_LENGTH = 48
PAST_WINDOW_DAYS = 30
FUTURE_WINDOW_DAYS = 365
SUBSCRIPTION_REFRESH_INTERVAL = "PT1H"
ICS_CACHE_SECONDS = 300


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _normalize_token(raw: str | None) -> str:
    token = str(raw or "").strip().strip("/")
    if token.endswith(".ics"):
        token = token[:-4]
    return token.strip()


def _subscription_path_suffix(token: str) -> str:
    return f"/calendar/subscriptions/staff/{quote(token)}.ics"


def _subscription_url(token: str) -> str:
    return f"{frappe.utils.get_url()}{_subscription_path_suffix(token)}"


def _webcal_url(feed_url: str) -> str:
    parts = urlsplit(feed_url)
    if parts.scheme in {"http", "https"}:
        return urlunsplit(("webcal", parts.netloc, parts.path, parts.query, parts.fragment))
    return feed_url


def _get_decrypted_token(subscription_name: str) -> str:
    try:
        from frappe.utils.password import get_decrypted_password

        token = (
            get_decrypted_password(
                CALENDAR_SUBSCRIPTION_DOCTYPE,
                subscription_name,
                "token_secret",
                raise_exception=False,
            )
            or ""
        )
        if token:
            return token
    except Exception:
        pass

    return str(frappe.db.get_value(CALENDAR_SUBSCRIPTION_DOCTYPE, subscription_name, "token_secret") or "").strip()


def _require_staff_subscription_context(user: str | None = None) -> dict[str, Any]:
    resolved_user = (user or frappe.session.user or "").strip()
    if not resolved_user or resolved_user == "Guest":
        frappe.throw(_("Please sign in to manage your calendar subscription."), frappe.PermissionError)

    employee = _resolve_employee_for_user(
        resolved_user,
        fields=["name", "employee_full_name", "school", "organization"],
        employment_status_filter=["!=", "Inactive"],
    )
    if not employee:
        frappe.throw(
            _("Your user is not linked to an active Employee record, so a staff calendar link cannot be created."),
            frappe.PermissionError,
        )

    return {
        "user": resolved_user,
        "employee": employee,
    }


def _active_subscription_rows_for_user(user: str) -> list[dict[str, Any]]:
    return (
        frappe.get_all(
            CALENDAR_SUBSCRIPTION_DOCTYPE,
            filters={
                "user": user,
                "feed_type": STAFF_FEED_TYPE,
                "subject_type": STAFF_SUBJECT_TYPE,
                "status": "Active",
            },
            fields=[
                "name",
                "user",
                "employee",
                "feed_type",
                "subject_type",
                "status",
                "token_hint",
                "creation",
                "modified",
            ],
            order_by="creation desc",
            limit=5,
            ignore_permissions=True,
        )
        or []
    )


def _active_subscription_row_for_user(user: str) -> dict[str, Any] | None:
    rows = _active_subscription_rows_for_user(user)
    return rows[0] if rows else None


def _build_subscription_response(row: dict[str, Any] | None, *, context: dict[str, Any]) -> dict[str, Any]:
    employee = context.get("employee") or {}
    payload: dict[str, Any] = {
        "active": False,
        "feed_url": None,
        "webcal_url": None,
        "google_url": None,
        "token_hint": None,
        "created_on": None,
        "modified": None,
        "viewer": {
            "user": context.get("user"),
            "employee": employee.get("name"),
            "employee_full_name": employee.get("employee_full_name"),
            "school": employee.get("school"),
            "organization": employee.get("organization"),
        },
        "feed": {
            "type": STAFF_FEED_TYPE,
            "subject_type": STAFF_SUBJECT_TYPE,
            "sources": list(STAFF_SUBSCRIPTION_SOURCES),
            "past_window_days": PAST_WINDOW_DAYS,
            "future_window_days": FUTURE_WINDOW_DAYS,
            "refresh_interval": SUBSCRIPTION_REFRESH_INTERVAL,
            "weekly_off_hidden": True,
        },
    }
    if not row:
        return payload

    token = _get_decrypted_token(row.get("name"))
    feed_url = _subscription_url(token) if token else None
    payload.update(
        {
            "active": True,
            "feed_url": feed_url,
            "webcal_url": _webcal_url(feed_url) if feed_url else None,
            "google_url": feed_url,
            "token_hint": row.get("token_hint"),
            "created_on": row.get("creation"),
            "modified": row.get("modified"),
        }
    )
    return payload


@frappe.whitelist()
def get_my_staff_calendar_subscription() -> dict[str, Any]:
    context = _require_staff_subscription_context()
    return _build_subscription_response(_active_subscription_row_for_user(context["user"]), context=context)


def _new_subscription_doc(*, context: dict[str, Any], token: str):
    employee = context.get("employee") or {}
    return frappe.get_doc(
        {
            "doctype": CALENDAR_SUBSCRIPTION_DOCTYPE,
            "user": context.get("user"),
            "employee": employee.get("name"),
            "feed_type": STAFF_FEED_TYPE,
            "subject_type": STAFF_SUBJECT_TYPE,
            "status": "Active",
            "token_hash": _token_hash(token),
            "token_secret": token,
            "token_hint": token[-8:],
        }
    )


@frappe.whitelist()
def create_or_get_my_staff_calendar_subscription() -> dict[str, Any]:
    context = _require_staff_subscription_context()
    row = _active_subscription_row_for_user(context["user"])
    if row:
        return _build_subscription_response(row, context=context)

    token = frappe.generate_hash(length=TOKEN_LENGTH)
    doc = _new_subscription_doc(context=context, token=token)
    doc.insert(ignore_permissions=True)

    row = _active_subscription_row_for_user(context["user"])
    return _build_subscription_response(row, context=context)


def _revoke_subscription_rows(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        frappe.db.set_value(
            CALENDAR_SUBSCRIPTION_DOCTYPE,
            name,
            {
                "status": "Revoked",
                "revoked_on": now_datetime(),
            },
            update_modified=True,
        )


@frappe.whitelist()
def reset_my_staff_calendar_subscription() -> dict[str, Any]:
    context = _require_staff_subscription_context()
    _revoke_subscription_rows(_active_subscription_rows_for_user(context["user"]))

    token = frappe.generate_hash(length=TOKEN_LENGTH)
    doc = _new_subscription_doc(context=context, token=token)
    doc.insert(ignore_permissions=True)

    row = _active_subscription_row_for_user(context["user"])
    return _build_subscription_response(row, context=context)


def _resolve_subscription_token(token: str | None) -> dict[str, Any]:
    normalized = _normalize_token(token)
    if not normalized:
        frappe.throw(_("Calendar subscription link is missing."), frappe.PermissionError)

    row = frappe.db.get_value(
        CALENDAR_SUBSCRIPTION_DOCTYPE,
        {
            "token_hash": _token_hash(normalized),
            "status": "Active",
            "feed_type": STAFF_FEED_TYPE,
            "subject_type": STAFF_SUBJECT_TYPE,
        },
        ["name", "user", "employee", "token_hint", "creation", "modified"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Calendar subscription link is invalid or has been reset."), frappe.PermissionError)

    _require_staff_subscription_context(row.get("user"))
    return row


def _subscription_window() -> tuple[datetime, datetime]:
    tzinfo = _system_tzinfo()
    local_now = _localize_datetime(now_datetime(), tzinfo)
    start_date = (local_now - timedelta(days=PAST_WINDOW_DAYS)).date()
    end_date = (local_now + timedelta(days=FUTURE_WINDOW_DAYS + 1)).date()
    return (
        tzinfo.localize(datetime.combine(start_date, time.min)),
        tzinfo.localize(datetime.combine(end_date, time.min)),
    )


def _event_is_weekly_off(event: dict[str, Any]) -> bool:
    if event.get("source") != "staff_holiday":
        return False
    meta = event.get("meta") if isinstance(event.get("meta"), dict) else {}
    return bool(int(meta.get("weekly_off") or 0))


def _subscription_events(payload: dict[str, Any]) -> list[dict[str, Any]]:
    events = payload.get("events") if isinstance(payload, dict) else []
    return [event for event in events or [] if isinstance(event, dict) and not _event_is_weekly_off(event)]


def _site_uid_host() -> str:
    parts = urlsplit(frappe.utils.get_url())
    return parts.netloc or frappe.local.site or "ifitwala-ed.local"


def _parse_event_datetime(value, tzinfo):
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            dt = get_datetime(value)
    else:
        dt = get_datetime(value)
    if dt.tzinfo:
        return dt.astimezone(tzinfo)
    return tzinfo.localize(dt)


def _format_utc_datetime(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _format_date_value(dt: datetime) -> str:
    return dt.date().strftime("%Y%m%d")


def _ical_escape(value) -> str:
    text = str(value or "")
    text = text.replace("\\", "\\\\")
    text = text.replace(";", "\\;")
    text = text.replace(",", "\\,")
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")
    return text


def _fold_ical_line(line: str) -> list[str]:
    if len(line.encode("utf-8")) <= 75:
        return [line]

    folded: list[str] = []
    current = ""
    current_len = 0
    for char in line:
        char_len = len(char.encode("utf-8"))
        if current and current_len + char_len > 75:
            folded.append(current)
            current = f" {char}"
            current_len = 1 + char_len
            continue
        current += char
        current_len += char_len

    if current:
        folded.append(current)
    return folded


def _ical_lines(lines: list[str]) -> str:
    folded: list[str] = []
    for line in lines:
        folded.extend(_fold_ical_line(line))
    return "\r\n".join(folded) + "\r\n"


def _event_uid(event: dict[str, Any], host: str) -> str:
    source_id = str(event.get("id") or event.get("name") or "")
    digest = hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:32]
    return f"ifitwala-ed-{digest}@{host}"


def _event_lines(event: dict[str, Any], *, tzinfo, generated_at: datetime, host: str) -> list[str]:
    start = _parse_event_datetime(event.get("start"), tzinfo)
    end = _parse_event_datetime(event.get("end") or event.get("start"), tzinfo)
    all_day = bool(event.get("allDay"))
    if end <= start:
        end = start + (timedelta(days=1) if all_day else timedelta(minutes=45))

    meta = event.get("meta") if isinstance(event.get("meta"), dict) else {}
    location = (meta.get("location") or "").strip()
    source = str(event.get("source") or "").strip()

    lines = [
        "BEGIN:VEVENT",
        f"UID:{_event_uid(event, host)}",
        f"DTSTAMP:{_format_utc_datetime(generated_at)}",
        f"SUMMARY:{_ical_escape(event.get('title') or _('Calendar Event'))}",
    ]
    if all_day:
        lines.extend(
            [
                f"DTSTART;VALUE=DATE:{_format_date_value(start)}",
                f"DTEND;VALUE=DATE:{_format_date_value(end)}",
            ]
        )
    else:
        lines.extend(
            [
                f"DTSTART:{_format_utc_datetime(start)}",
                f"DTEND:{_format_utc_datetime(end)}",
            ]
        )
    if location:
        lines.append(f"LOCATION:{_ical_escape(location)}")
    lines.extend(
        [
            f"DESCRIPTION:{_ical_escape(_('Open Ifitwala Ed for full details.'))}",
            f"CATEGORIES:{_ical_escape(source)}",
            "TRANSP:OPAQUE" if source in {"student_group", "meeting"} else "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]
    )
    return lines


def build_staff_calendar_ics(*, payload: dict[str, Any], subscription: dict[str, Any]) -> str:
    tzinfo = _system_tzinfo()
    generated_at = _localize_datetime(now_datetime(), tzinfo)
    host = _site_uid_host()
    calendar_name = _("Ifitwala Staff Calendar")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Ifitwala Ed//Staff Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"NAME:{_ical_escape(calendar_name)}",
        f"X-WR-CALNAME:{_ical_escape(calendar_name)}",
        f"X-WR-TIMEZONE:{_ical_escape(tzinfo.zone)}",
        f"REFRESH-INTERVAL;VALUE=DURATION:{SUBSCRIPTION_REFRESH_INTERVAL}",
        f"X-PUBLISHED-TTL:{SUBSCRIPTION_REFRESH_INTERVAL}",
    ]

    for event in _subscription_events(payload):
        lines.extend(_event_lines(event, tzinfo=tzinfo, generated_at=generated_at, host=host))

    lines.append("END:VCALENDAR")
    return _ical_lines(lines)


def _set_ics_response(ics_text: str) -> None:
    frappe.local.response["type"] = "download"
    frappe.local.response["filename"] = "ifitwala-staff-calendar.ics"
    frappe.local.response["filecontent"] = ics_text.encode("utf-8")
    frappe.local.response["display_content_as"] = "inline"
    frappe.local.response["content_type"] = "text/calendar; charset=utf-8"
    headers = frappe.local.response.setdefault("headers", {})
    headers["Cache-Control"] = f"private, max-age={ICS_CACHE_SECONDS}, must-revalidate"


def serve_staff_calendar_subscription(token: str | None) -> None:
    subscription = _resolve_subscription_token(token)
    window_start, window_end = _subscription_window()
    payload = calendar_staff_feed.get_staff_calendar_for_user(
        user=subscription.get("user"),
        from_datetime=window_start.isoformat(),
        to_datetime=window_end.isoformat(),
        sources=list(STAFF_SUBSCRIPTION_SOURCES),
        force_refresh=False,
    )
    _set_ics_response(build_staff_calendar_ics(payload=payload, subscription=subscription))


@frappe.whitelist(allow_guest=True)
def download_staff_calendar_subscription(token: str | None = None) -> None:
    serve_staff_calendar_subscription(token)
