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

    SchoolEventParticipant = frappe.qb.DocType("School Event Participant")
    SchoolCalendar = frappe.qb.DocType("SchoolCalendar")

    query = (
        frappe.qb.from_(SchoolCalendar)
        .left_join(SchoolEventParticipant)
        .on(SchoolCalendar.name == SchoolEventParticipant.parent)
        .where(
            (SchoolEventParticipant.participant == user) | (SchoolCalendar.owner == user)
        )
    ).select(SchoolCalendar.name)

    return query

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
	"""
	Fetches school events within a specified date range and filters.

	Args:
		start (str): The start date for fetching events.
		end (str): The end date for fetching events.
		user (str, optional): The user for whom to fetch events. Defaults to the current session user.
		filters (dict or str, optional): Additional filters for fetching events. Can be a dictionary or a JSON string.

	Returns:
		list: A list of dictionaries containing event details.
	"""
	if not user:
		user = frappe.session.user

	if isinstance(filters, string_types):
		filters = json.loads(filters)

	filters_condition = get_filters_cond('School Event', filters, [])

	tables = ["`tabSchool Event`"]
	if "`tabSchool Event Participants`" in filters_condition:
		tables.append("`tabSchool Event Participants`")
		
	events = frappe.db.sql(
		"""
		SELECT
			`tabSchool Event`.name,
			`tabSchool Event`.subject,
			`tabSchool Event`.color,
			`tabSchool Event`.starts_on,
			`tabSchool Event`.ends_on,
			`tabSchool Event`.owner,
			`tabSchool Event`.all_day,
			`tabSchool Event`.event_category,
			`tabSchool Event`.school,
			`tabSchool Event`.room
		FROM {tables}
		WHERE
			(date(`tabSchool Event`.starts_on) BETWEEN date(%(start)s) AND date(%(end)s))
			OR (date(`tabSchool Event`.ends_on) BETWEEN date(%(start)s) AND date(%(end)s))
		{filters_condition}
		ORDER BY `tabSchool Event`.starts_on
		""".format(tables=", ".join(tables), filter_condition=filter_condition),
		{"start": start, "end": end, "user": user},
		as_dict=1
	)
	allowed_events = []
	for event in events:
		if frappe.get_doc("School Event", event.name).has_permission():
			allowed_events.append(event)

	return allowed_events