# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from six import string_types
from frappe import _
from frappe.utils import get_datetime, now_datetime
from frappe.model.document import Document
from frappe.desk.reportview import get_filters_cond
from frappe.permissions import has_permission

class SchoolEvent(Document):
	def validate(self):
		self.validate_time()

	def on_update(self):
		self.validate_date()

	def validate_date(self):
		if (self.event_category != "Other") and (get_datetime(self.starts_on) < get_datetime(now_datetime())):
			frappe.throw(_("The date {0} of the event has to be in the future. Please adjust the date.").format(self.starts_on))

	def validate_time(self):
		if get_datetime(self.starts_on) > get_datetime(self.ends_on):
			frappe.throw(_("The start time of your event {0} has to be earlier than its end {1}. Please adjust the time.").format(self.starts_on, self.ends_on))


# def get_permission_query_conditions(user):
#	if not user:
#		user = frappe.session.user
#
#	return """(name in (select parent from `tabSchool Event Participant`where participant=%(user)s) or owner=%(user)s)""" % {
#			"user": frappe.db.escape(user),
#		}

def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    participant = frappe.qb.DocType("School Event Participant")
    event = frappe.qb.DocType("School Event")  # Correct table

    query = (
        frappe.qb.from_(participant)
        .join(event).on(participant.parent == event.name)  # Correct join condition
        .where(participant.participant == user)
        .select(event.name)  # Select the event name
    )

    names = [r[0] for r in query.run()]  # Get all event names

    if names:
        name_condition = f"name IN ({', '.join([frappe.db.escape(n) for n in names])})"
    else:
        name_condition = "" # Handle no participants

    owner_condition = f"owner = {frappe.db.escape(user)}"

    if name_condition:
        combined_condition = f"({name_condition} OR {owner_condition})"
    else:
        combined_condition = owner_condition

    return combined_condition


def event_has_permission(doc, user):
	if doc.is_new():
		return True
	if doc.event_type=="Public":
		return True
	#if doc.owner == user or user in [d.participant for d in doc.participants]:
	if doc.event_type == "Private" and (doc.owner == user or user in [d.participant for d in doc.participants]):
		return True
	if doc.event_category == "Course":
		stu_group = frappe.get_doc("Student Group", doc.reference_name)
		if user in [ins.user_id for ins in stu_group.instructors] or user in [stu.user_id for stu in stu_group.students]:
			return True
	return False


@frappe.whitelist()
def get_school_events(start, end, user=None, filters=None):
	if not user:
		user = frappe.session.user

	if isinstance(filters, string_types):
		filters = json.loads(filters)

	filters_condition = get_filters_cond("School Event", filters, [])

	tables = ["`tabSchool Event`"]
	if "`tabSchool Event Participant`" in filters_condition:
		tables.append("`tabSchool Event Participant`")
		
	events = frappe.db.sql(
		f"""
		SELECT `tabSchool Event`.* 
		FROM `tabSchool Event` 
		LEFT JOIN `tabSchool Event Participant` ON `tabSchool Event`.name = `tabSchool Event Participant`.parent
		WHERE
			(DATE(`tabSchool Event`.starts_on) BETWEEN DATE(%(start)s) AND DATE(%(end)s))
			OR (DATE(`tabSchool Event`.ends_on) BETWEEN DATE(%(start)s) AND DATE(%(end)s))
			{filters_condition} 
		ORDER BY `tabSchool Event`.starts_on
		""", 
		{"start": start, "end": end},
		as_dict=True, 
	)
	allowed_events = []
	for event in events:
		if frappe.get_doc("School Event", event["name"]).has_permission(user=user):
			allowed_events.append(event)

	return allowed_events
