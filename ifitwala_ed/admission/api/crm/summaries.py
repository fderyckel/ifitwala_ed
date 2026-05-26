# ifitwala_ed/admission/api/crm/summaries.py

from __future__ import annotations

import frappe


def _conversation_summary(conversation_name: str) -> dict:
    row = frappe.db.get_value(
        "Admission Conversation",
        conversation_name,
        [
            "name",
            "title",
            "organization",
            "school",
            "assigned_to",
            "status",
            "inquiry",
            "student_applicant",
            "external_identity",
            "channel_account",
            "latest_message_at",
            "latest_inbound_message_at",
            "latest_outbound_message_at",
            "needs_reply",
            "last_message_preview",
            "next_action_on",
            "last_activity_at",
        ],
        as_dict=True,
    )
    return dict(row or {})


def _message_summary(message_name: str) -> dict:
    row = frappe.db.get_value(
        "Admission Message",
        message_name,
        [
            "name",
            "conversation",
            "direction",
            "message_type",
            "delivery_status",
            "message_at",
            "linked_inquiry",
            "linked_student_applicant",
            "media_status",
        ],
        as_dict=True,
    )
    return dict(row or {})


def _activity_summary(activity_name: str) -> dict:
    row = frappe.db.get_value(
        "Admission CRM Activity",
        activity_name,
        [
            "name",
            "conversation",
            "activity_type",
            "activity_channel",
            "outcome",
            "next_action_on",
            "staff_user",
            "activity_at",
        ],
        as_dict=True,
    )
    return dict(row or {})


def _inquiry_summary(inquiry_name: str) -> dict:
    row = frappe.db.get_value(
        "Inquiry",
        inquiry_name,
        [
            "name",
            "workflow_state",
            "assigned_to",
            "assignment_lane",
            "archive_reason",
            "organization",
            "school",
            "student_applicant",
            "first_contacted_at",
            "followup_due_on",
            "sla_status",
        ],
        as_dict=True,
    )
    return dict(row or {})


def _applicant_summary(applicant_name: str) -> dict:
    row = frappe.db.get_value(
        "Student Applicant",
        applicant_name,
        ["name", "application_status", "organization", "school", "inquiry"],
        as_dict=True,
    )
    return dict(row or {})
