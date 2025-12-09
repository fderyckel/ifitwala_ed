# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today, add_days, getdate, strip_html
from ifitwala_ed.api.org_comm_utils import check_audience_match

@frappe.whitelist()
def get_org_communication_feed(
    search_text: str | None = None,
    status: str | None = "PublishedOrArchived",
    priority: str | None = None,
    portal_surface: str | None = None,
    communication_type: str | None = None,
    date_range: str | None = "90d",  # '7d' | '30d' | '90d' | 'year' | 'all'
    only_with_interactions: int | None = 0,
    limit_start: int = 0,
    limit_page_length: int = 30,
) -> dict:
    
    user = frappe.session.user
    roles = frappe.get_roles(user)
    employee = frappe.db.get_value("Employee", {"user_id": user},
        ["name", "school", "organization", "department"],
        as_dict=True
    )
    
    # Base Filters
    conditions = []
    values = {}
    
    # Status
    if status == "PublishedOrArchived":
        conditions.append("status IN ('Published', 'Archived')")
    elif status == "Published":
        conditions.append("status = 'Published'")
    elif status == "All":
        # No status filter, effectively allows Draft/Scheduled if user has permissions (though audience check handles visibility too)
        # But usually 'All' in this context means all VISIBLE statuses. 
        # For simplicity and safety, let's assume 'All' still means Published/Archived/Scheduled/Draft?
        # The spec says: "All" -> no status filter.
        pass
    elif status:
        conditions.append("status = %(status)s")
        values["status"] = status
        
    # Priority
    if priority and priority != "All":
        conditions.append("priority = %(priority)s")
        values["priority"] = priority
        
    # Portal Surface
    if portal_surface and portal_surface != "All":
        conditions.append("portal_surface = %(portal_surface)s")
        values["portal_surface"] = portal_surface
        
    # Communication Type
    if communication_type and communication_type != "All":
        conditions.append("communication_type = %(communication_type)s")
        values["communication_type"] = communication_type
        
    # Date Range (publish_from)
    if date_range and date_range != "all":
        end_date = getdate(today())
        start_date = None
        
        if date_range == "7d":
            start_date = add_days(end_date, -7)
        elif date_range == "30d":
            start_date = add_days(end_date, -30)
        elif date_range == "90d":
            start_date = add_days(end_date, -90)
        elif date_range == "year":
            # Current calendar year
            start_date = f"{end_date.year}-01-01"
            
        if start_date:
            conditions.append("publish_from >= %(start_date)s")
            values["start_date"] = start_date
            
    # Search Text
    if search_text:
        conditions.append("(title LIKE %(search)s OR message LIKE %(search)s)")
        values["search"] = f"%{search_text}%"
        
    # Only with interactions
    # optimizing this: first find comms with interactions for this user? 
    # Spec: "at least one Communication Interaction row for this user or at all (your choice; I’d start with “any interaction at all”)"
    # Let's go with "any interaction at all" as it's broader.
    if only_with_interactions:
        # Check existence of interaction
        conditions.append("EXISTS (SELECT name FROM `tabCommunication Interaction` WHERE org_communication = `tabOrg Communication`.name)")

    where_clause = " AND ".join(conditions)
    if where_clause:
        where_clause = "WHERE " + where_clause
        
    # Fetch candidates
    # We fetch more than limit to handle post-query audience filtering
    # Since audience check is python-side, pagination is tricky. 
    # We might need to fetch a batch, filter, and fetch more if needed?
    # OR, for V1, just fetch a larger slice and filter in memory? 
    # Given typical volume, fetching matching candidates sorted by date and filtering in python is clearer but inefficient for huge data.
    # However, audience check logic is complex SQL-wise.
    # Let's try to fetch a reasonable buffer. 
    # Or, we can acknowledge that limit_start/length applies to the RESULT list, so we must scan.
    
    # Strategy:
    # 1. Query candidate IDs sorted by priority/date.
    # 2. Iterate and check audience match until we fill the page.
    
    sql = f"""
        SELECT
            name,
            title,
            message,
            communication_type,
            status,
            priority,
            portal_surface,
            school,
            organization,
            publish_from,
            publish_to,
            brief_start_date,
            brief_end_date,
            interaction_mode,
            allow_private_notes,
            allow_public_thread
        FROM `tabOrg Communication`
        {where_clause}
        ORDER BY publish_from DESC, creation DESC
    """
    
    candidates = frappe.db.sql(sql, values, as_dict=True)
    
    visible_items = []
    
    # Post-filtering for audience
    for c in candidates:
        if check_audience_match(c.name, user, roles, employee):
            # Format item
            visible_items.append({
                "name": c.name,
                "title": c.title,
                "communication_type": c.communication_type,
                "status": c.status,
                "priority": c.priority,
                "portal_surface": c.portal_surface,
                "school": c.school,
                "organization": c.organization,
                "publish_from": c.publish_from,
                "publish_to": c.publish_to,
                "brief_start_date": c.brief_start_date,
                "brief_end_date": c.brief_end_date,
                "interaction_mode": c.interaction_mode,
                "allow_private_notes": c.allow_private_notes,
                "allow_public_thread": c.allow_public_thread,
                "snippet": (strip_html(c.message) or "")[:260] + "..." if c.message and len(strip_html(c.message)) > 260 else (strip_html(c.message) or ""),
                "has_active_thread": c.allow_public_thread,
                "audience_label": get_audience_label(c.name)
            })
            
    # Apply pagination on the filtered list
    total_count = len(visible_items)
    
    # Slice
    start = int(limit_start)
    length = int(limit_page_length)
    paged_items = visible_items[start : start + length]
    
    return {
        "items": paged_items,
        "total_count": total_count,
        "limit_start": start,
        "limit_page_length": length,
        "has_more": (start + length) < total_count
    }

def get_audience_label(comm_name):
    # Quick helper to generate a human-readable audience summary
    # e.g. "Whole Staff · Ifitwala Secondary School"
    audiences = frappe.get_all("Org Communication Audience", filters={"parent": comm_name}, fields=["target_group", "school", "team"])
    if not audiences:
        return "Whole Organization"
        
    parts = []
    for a in audiences:
        label = a.target_group or a.team or "Everyone"
        if a.school:
            school_name = frappe.db.get_value("School", a.school, "school_name") # Fix: school uses school_name, not title
            label += f" · {school_name or a.school}"
        parts.append(label)
        
    return ", ".join(parts)
