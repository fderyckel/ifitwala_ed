# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/setup/doctype/meeting/meeting.py

import frappe
from frappe import _
from frappe.model.document import Document

class Meeting(Document):

    def validate(self):
        self.ensure_team_selected()
        self.ensure_participants_from_team()
        self.ensure_at_least_one_participant()
        self.validate_time_logic()
        self.validate_minutes_when_completed()

    def ensure_team_selected(self):
        if not self.team:
            frappe.throw(_("Please select a Team for the meeting."))

    def ensure_participants_from_team(self):
        # If participants table is empty, auto-populate with active team members
        if not self.get("participants"):
            team_members = frappe.db.get_all(
                "Team Member",
                filters={"parent": self.team, "active": 1},
                fields=["member"]
            )
            for m in team_members:
                self.append("participants", {
                    "participant": m.member,
                    "role_in_meeting": "Participant",
                    "attendance_status": "Absent"
                })

    def ensure_at_least_one_participant(self):
        if not self.get("participants") or len(self.get("participants")) < 1:
            frappe.throw(_("Meeting must have at least one participant."))

    def validate_time_logic(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            frappe.throw(_("End Time must be later than Start Time."))

    def validate_minutes_when_completed(self):
        if self.status == "Completed" and not self.minutes:
            frappe.throw(_("Minutes must be entered if the meeting status is ‘Completed’."))

    def on_submit(self):
        # Placeholder: e.g., send notifications, mark follow-up creation
        pass

