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

        # Fetch existing rotation days
        existing_rotation_days = frappe.get_all("School Schedule Day",
            filters={"parent": self.name},
            fields=["rotation_day"]
        )

        rotation_day_count = len(existing_rotation_days)

        # Check for mismatch
        if rotation_day_count > self.rotation_days:
            frappe.throw(
                f"You have defined {rotation_day_count} rotation days, "
                f"but the schedule allows only {self.rotation_days}. "
                "Please remove the excess rotation days."
            )

        if rotation_day_count < self.rotation_days:
            frappe.throw(
                f"You have defined only {rotation_day_count} rotation days, "
                f"but the schedule requires {self.rotation_days}. "
                "Please add the missing rotation days."
            )      

    @frappe.whitelist()
    def generate_rotation_days(self, overwrite=False): 
        """Generate rotation days based on rotation_days count, allowing overwrite if requested."""
        
        if not self.rotation_days or self.rotation_days <= 0: 
            frappe.throw("Please set a valid number of rotation days before generating.")

        # Check existing rotation days
        existing_days = frappe.get_all(
            "School Schedule Day",
            filters={"parent": self.name},
            fields=["rotation_day"]
        )

        if existing_days and not overwrite:
            frappe.throw(
            "Rotation days already exist. If you want to regenerate them, please clear them first "
            "or use the overwrite option."
            )

        # Clear existing rotation days if overwrite is enabled
        if existing_days and overwrite:
            frappe.db.sql("""DELETE FROM `tabSchool Schedule Day`
                WHERE parent=%s""",(self.name,))
            frappe.db.commit()

        # Generate new rotation days
        for day in range(1, self.rotation_days + 1):
            rotation_label = f"Day {day}"  # Default label
            schedule_day = frappe.get_doc({
            "doctype": "School Schedule Day",
            "parent": self.name,
            "parentfield": "school_schedule_day",
            "parenttype": "School Schedule",
            "rotation_day": day,
            "rotation_label": rotation_label,
            "num_blocks": 0  # Default value, user must update later
            })
            schedule_day.insert(ignore_permissions=True)

        frappe.msgprint(f"{self.rotation_days} Rotation Days have been generated.")


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
            frappe.throw("No School Schedule Days found. Please generate rotation days first.")

        for day in schedule_days:
            if day["num_blocks"] <= 0:
                frappe.throw(
                    f"Rotation Day {day['rotation_day']} does not have a valid number of blocks. "
                    "Please set the number of blocks before generating them."
                )

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
                    "parentfield": "course_schedule_block",
                    "parenttype": "School Schedule",
                    "rotation_day": day["rotation_day"],
                    "block_number": block_number
                })
                block.insert(ignore_permissions=True)

        frappe.msgprint("School Schedule Blocks have been generated.")
