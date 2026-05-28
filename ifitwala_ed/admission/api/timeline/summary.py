from __future__ import annotations

from collections import Counter

from frappe import _

from ifitwala_ed.admission.api.timeline.ladder import _completion_ladder
from ifitwala_ed.admission.api.timeline.utils import _as_bool, _as_text


def _summary(
    *,
    items: list[dict],
    context: dict,
    case_summary: dict,
    conversations: list[dict],
    plans: list[dict],
    requests: list[dict],
    enrollments: list[dict],
) -> dict:
    counts = Counter(item["kind"] for item in items)
    latest = max((item.get("_sort_at") for item in items if item.get("_sort_at")), default=None)
    return {
        "headline": _("Admissions relationship timeline"),
        "latest_at": _as_text(latest),
        "needs_reply": _as_bool(case_summary.get("needs_reply"))
        or any(_as_bool(row.get("needs_reply")) for row in conversations),
        "counts": dict(counts),
        "completion_ladder": _completion_ladder(
            inquiry=context.get("inquiry"),
            applicant=context.get("applicant"),
            plans=plans,
            requests=requests,
            enrollments=enrollments,
        ),
    }
