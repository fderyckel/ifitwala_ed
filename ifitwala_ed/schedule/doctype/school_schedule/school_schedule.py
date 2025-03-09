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
        if self.get("school_schedule_day") and not overwrite:
            frappe.throw(
                "Rotation days already exist. If you want to regenerate them, please clear them first "
                "or use the overwrite option."
            )

        # Clear existing rotation days if overwrite is enabled
        if self.get("school_schedule_day") and overwrite:
            self.set("school_schedule_day", [])  # Clears the child table

        # Generate new rotation days and append them to the child table
        for day in range(1, self.rotation_days + 1):
            rotation_label = f"Day {day}"  # Default label
            schedule_day = self.append("school_schedule_day", {})
            schedule_day.rotation_day = day
            schedule_day.rotation_label = rotation_label
            schedule_day.num_blocks = 0  # Default value, user must update later

        # Save the document to persist the changes
        self.save()

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
    def generate_blocks(self, overwrite=False):
        """Manually generate School Schedule Blocks based on School Schedule Days."""

        if not self.get("school_schedule_day"):
            frappe.throw("No School Schedule Days found. Please generate rotation days first.")

        # Check if blocks already exist in the child table
        if self.get("course_schedule_block") and not overwrite:
            frappe.throw(
                "Blocks already exist. If you want to regenerate them, please clear them first "
                "or use the overwrite option."
            )

        # Clear existing blocks if overwrite is enabled
        if self.get("course_schedule_block") and overwrite:
            self.set("course_schedule_block", [])  # Clears the blocks child table

        # Generate blocks for each rotation day
        for day in self.get("school_schedule_day"):
            if day.num_blocks <= 0:
                frappe.throw(
                    f"Rotation Day {day.rotation_day} does not have a valid number of blocks. "
                    "Please set the number of blocks before generating them."
                )

            for block_number in range(1, day.num_blocks + 1):
                block = self.append("course_schedule_block", {})
                block.rotation_day = day.rotation_day
                block.block_number = block_number

        # Save the document to persist the changes
        self.save()

        frappe.msgprint("School Schedule Blocks have been generated.")

