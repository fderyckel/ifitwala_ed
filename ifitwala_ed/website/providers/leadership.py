# ifitwala_ed/website/providers/leadership.py

import frappe
from frappe.utils import cint
from frappe.utils.caching import redis_cache

from ifitwala_ed.website.utils import build_image_variants


@redis_cache(ttl=3600)
def _get_leaders(school: str, roles: tuple[str, ...], limit: int):
    filters = {
        "school": school,
        "show_on_website": 1,
    }
    if roles:
        filters["designation"] = ["in", list(roles)]

    leaders = frappe.get_all(
        "Employee",
        filters=filters,
        fields=["employee_full_name", "employee_image", "designation", "small_bio"],
        order_by="modified desc",
        limit_page_length=limit,
    )

    items = []
    for leader in leaders:
        items.append(
            {
                "name": leader.get("employee_full_name"),
                "title": leader.get("designation"),
                "bio": leader.get("small_bio"),
                "photo": build_image_variants(leader.get("employee_image"), "employee"),
            }
        )
    return items


def get_context(*, school, page, block_props):
    """
    Leadership / authority block.
    """
    limit = max(cint(block_props.get("limit") or 4), 1)
    roles = tuple(block_props.get("roles") or [])
    leaders = _get_leaders(school=school.name, roles=roles, limit=limit)

    return {
        "data": {
            "title": block_props.get("title"),
            "leaders": leaders,
        }
    }
