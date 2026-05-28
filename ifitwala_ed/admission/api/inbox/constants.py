from __future__ import annotations

DEFAULT_LIMIT = 40
MAX_LIMIT = 100
STALE_LEAD_DAYS = 14


QUEUE_IDS = (
    "needs_reply",
    "unassigned",
    "overdue_first_contact",
    "due_today",
    "qualified_not_invited",
    "invited_not_started",
    "missing_documents",
    "stale_leads",
    "unmatched_messages",
)
