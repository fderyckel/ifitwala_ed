# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import timedelta


class SchoolSchedule(Document):
    """Handles school schedule configurations."""

    def validate(self):
        """Validate that the selected School Calendar belongs to the same School."""
        if self.school_calendar:
            school_in_calendar = frappe.db.get_value("School Calendar", self.school_calendar, "school")
            if school_in_calendar and school_in_calendar != self.school:
                frappe.throw(
                    f"The selected School Calendar ({self.school_calendar}) belongs to a different School ({school_in_calendar}). "
                    f"Please choose a calendar associated with {self.school}."
                )

    @frappe.whitelist()
    def clear_schedule(self):
        """Deletes all School Schedule Days and Blocks."""
        frappe.db.sql(
            """
            DELETE FROM `tabSchool Schedule Block`
            WHERE parent=%s
            """,
            (self.name,)
        )
        frappe.db.sql(
            """
            DELETE FROM `tabSchool Schedule Day`
            WHERE parent=%s
            """,
            (self.name,)
        )
        frappe.db.commit()
        frappe.msgprint("School Schedule Days and Blocks have been cleared.")

    @frappe.whitelist()
    def generate_blocks(self):
        """Manually generate School Schedule Blocks based on School Schedule Days."""
        schedule_days = frappe.get_all(
            "School Schedule Day",
            filters={"parent": self.name},
            fields=["rotation_day", "num_blocks"]
        )

        if not schedule_days:
            frappe.throw("No School Schedule Days found. Please add rotation days first.")

        for day in schedule_days:
            existing_blocks = frappe.get_all(
                "School Schedule Block",
                filters={"parent": self.name, "rotation_day": day["rotation_day"]},
                fields=["name"]
            )

            # Skip if blocks already exist
            if existing_blocks:
                continue

            # Generate blocks
            for block_number in range(1, day["num_blocks"] + 1):
                block = frappe.get_doc({
                    "doctype": "School Schedule Block",
                    "parent": self.name,
                    "parentfield": "blocks",
                    "parenttype": "School Schedule",
                    "rotation_day": day["rotation_day"],
                    "block_number": block_number
                })
                block.insert(ignore_permissions=True)

        frappe.msgprint("School Schedule Blocks have been generated.")