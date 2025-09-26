# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

# ifitwala_ed/curriculum/doctype/lesson/lesson.py
from pydoc import doc
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils.caching import redis_cache


_STEP = 10
_ACTIVITY_STEP = 10

# Map your child row activity_type -> Task.delivery_type
_ACTIVITY_TO_DELIVERY = {
	"Reading": "Checkpoint",
	"Video": "Checkpoint",
	"Link": "Checkpoint",
	"Discussion": "Discussion",
	"Assignment": "Assignment",
}

class Lesson(Document):
	def before_insert(self):
		# If no lesson_order provided, append at the end (spaced by 10)
		if not int(self.lesson_order or 0):
			self.lesson_order = _next_lesson_order(self.learning_unit)

	def before_save(self):
		# Normalize empty/zero to next slot
		if not int(self.lesson_order or 0):
			self.lesson_order = _next_lesson_order(self.learning_unit)
			return

		# Guard against collisions within the same learning unit
		if self.learning_unit:
			exists = frappe.db.exists(
				"Lesson",
				{
					"learning_unit": self.learning_unit,
					"lesson_order": self.lesson_order,
					"name": ["!=", self.name],
				},
			)
			if exists:
				self.lesson_order = _next_lesson_order(self.learning_unit)

		# Keep child activity orders unique & spaced
		self._normalize_activity_orders()



	# Promote a Lesson Activity -> Task
	def promote_activity_to_task(
		self,
		activity_child_name: str,
		delivery_type: str | None = None,
		student_group: str | None = None,
		available_from: str | None = None,
		due_date: str | None = None,
		available_until: str | None = None,
		is_published: int | None = None,
	) -> dict:
		"""Create a Task from a Lesson Activity child row and return {"name": <task_name>}."""
		if not activity_child_name:
			frappe.throw(_("activity_child_name is required"))

		row = next((r for r in (self.get("activities") or []) if r.name == activity_child_name), None)
		if not row:
			frappe.throw(_("Activity row not found on this Lesson."))

		resolved_delivery = (delivery_type or
			_ACTIVITY_TO_DELIVERY.get((row.activity_type or "").strip(), "Checkpoint"))

		payload = {
			"doctype": "Task",
			"title": row.title or _("Untitled Activity"),
			"delivery_type": resolved_delivery,
			# Context from this Lesson
			"course": self.get("course"),
			"learning_unit": self.get("learning_unit"),
			"lesson": self.name,
			# Audience (optional; Task.validate will enforce publish guard)
			"student_group": student_group,
			"available_from": available_from,
			"due_date": due_date,
			"available_until": available_until,
			"is_published": int(is_published) if is_published is not None else 0,
			# Defaults (non-graded for most promoted items unless author changes later)
			"is_graded": 0,
			"instructions": _compose_instructions_from_activity(row),
		}

		if resolved_delivery == "Assignment":
			payload.setdefault("submission_required", 1)
			payload.setdefault("submission_type", "Online Text")

		task = frappe.get_doc(payload)
		task.insert(ignore_permissions=False)
		return {"name": task.name}

	def _normalize_activity_orders(self) -> None:
		"""Ensure unique ascending `lesson_activity_order` values (10,20,30,...) on activities."""
		rows = self.get("activities") or []
		if not rows:
			return

		# Sort by current lesson_activity_order, then by idx for stability
		sorted_rows = sorted(rows, key=lambda r: (int(r.lesson_activity_order or 0), r.idx or 0))
		next_val = _ACTIVITY_STEP
		seen = set()

		for r in sorted_rows:
			curr = int(r.lesson_activity_order or 0)
			if curr <= 0 or curr in seen:
				r.lesson_activity_order = next_val
			else:
				r.lesson_activity_order = curr
			seen.add(int(r.lesson_activity_order))
			next_val = max(next_val + _ACTIVITY_STEP, int(r.lesson_activity_order) + _ACTIVITY_STEP)


# ----------------------------
# HELPERS
# ----------------------------

def _next_lesson_order(learning_unit: str) -> int:
	max_order = frappe.db.sql(
		"select coalesce(max(lesson_order), 0) from `tabLesson` where learning_unit=%s",
		(learning_unit,),
		as_list=True,
	)[0][0]
	return int(max_order) + _STEP


def _next_activity_order(lesson_name: str) -> int:
	max_order = frappe.db.sql(
		"select coalesce(max(`lesson_activity_order`), 0) from `tabLesson Activity` where parent=%s",
		(lesson_name,),
		as_list=True,
	)[0][0]
	return int(max_order) + _ACTIVITY_STEP

def _compose_instructions_from_activity(row) -> str:
	lines = []
	if getattr(row, "notes", None):
		lines.append(str(row.notes).strip())
	if getattr(row, "activity_type", "") == "Reading" and getattr(row, "reading_content", None):
		lines.append(_("— Reading excerpt (from lesson activity) —"))
		lines.append(str(row.reading_content).strip())
	if getattr(row, "activity_type", "") == "Video" and getattr(row, "video_url", None):
		lines.append(_("Video: {0}").format(row.video_url))
	if getattr(row, "external_link", None):
		lines.append(_("Link: {0}").format(row.external_link))
	return "\n\n".join([l for l in lines if l])



@frappe.whitelist()
def reorder_lessons(learning_unit: str, lesson_names):
	"""
	Bulk reorder Lessons for a Learning Unit in a single transaction.

	Args:
		learning_unit (str): Learning Unit name
		lesson_names (list|str): Ordered list of Lesson names. If str, JSON is parsed.

	Raises:
		frappe.PermissionError: if user lacks write permission on the Learning Unit.
		frappe.ValidationError: on duplicates, unknown lessons, or mismatched mapping.

	Returns:
		dict: {"updated": <count>, "order_step": 10}
	"""
	# Parse and validate payload
	if isinstance(lesson_names, str):
		lesson_names = frappe.parse_json(lesson_names)  # expects a JSON array of names

	if not isinstance(lesson_names, (list, tuple)) or not lesson_names:
		frappe.throw("lesson_names must be a non-empty list of Lesson names.", frappe.ValidationError)

	# Permission: require write on the Learning Unit
	if not frappe.has_permission("Learning Unit", ptype="write", doc=learning_unit):
		frappe.throw("Not permitted to reorder lessons for this learning unit.", frappe.PermissionError)

	# Duplicates check
	if len(lesson_names) != len(set(lesson_names)):
		frappe.throw("Duplicate Lesson names in payload.", frappe.ValidationError)

	# Fetch existing lessons for this learning unit
	existing = frappe.db.get_all(
		"Lesson",
		filters={"learning_unit": learning_unit},
		fields=["name"],
		pluck="name",
	)
	existing_set = set(existing)

	# Ensure payload lessons match existing (strict mode)
	payload_set = set(lesson_names)
	if existing_set != payload_set:
		missing = ", ".join(sorted(existing_set - payload_set)) or "-"
		extra = ", ".join(sorted(payload_set - existing_set)) or "-"
		frappe.throw(
			f"Lesson list mismatch.\nMissing in payload: {missing}\nNot in unit: {extra}",
			frappe.ValidationError,
		)

	# Prepare spaced order values (10,20,30…)
	values = [(name, (idx + 1) * _STEP) for idx, name in enumerate(lesson_names)]

	# Bulk update in one transaction
	frappe.db.bulk_update(
		"Lesson",
		fields=["lesson_order"],
		values=values,
	)

	return {"updated": len(values), "order_step": _STEP}


@frappe.whitelist()
def promote_activity_to_task(
	lesson: str,
	activity_child_name: str,
	delivery_type: str | None = None,
	student_group: str | None = None,
	available_from: str | None = None,
	due_date: str | None = None,
	available_until: str | None = None,
	is_published: int | None = None,
) -> dict:
	"""Thin RPC wrapper to call the instance method while preserving the public API path."""
	if not lesson:
		frappe.throw(_("lesson is required"))
	doc = frappe.get_doc("Lesson", lesson)
	return doc.promote_activity_to_task(
		activity_child_name=activity_child_name,
		delivery_type=delivery_type,
		student_group=student_group,
		available_from=available_from,
		due_date=due_date,
		available_until=available_until,
		is_published=is_published,
	)

@frappe.whitelist()
def bulk_promote_activities_to_tasks(
	lesson: str,
	activity_child_names,
	delivery_type: str | None = None,
	student_group: str | None = None,
	available_from: str | None = None,
	due_date: str | None = None,
	available_until: str | None = None,
	is_published: int | None = None,
):
	"""Promote multiple activity rows to Tasks. Returns {created: [...], failed: [{row, error}]}."""
	if isinstance(activity_child_names, str):
		activity_child_names = frappe.parse_json(activity_child_names)

	if not lesson or not activity_child_names:
		frappe.throw(_("lesson and activity_child_names are required"))

	doc = frappe.get_doc("Lesson", lesson)
	created, failed = [], []

	for child_name in activity_child_names:
		sp = f"bp_{child_name}"
		frappe.db.savepoint(sp)
		try:
			res = doc.promote_activity_to_task(
				activity_child_name=child_name,
				delivery_type=delivery_type,
				student_group=student_group,
				available_from=available_from,
				due_date=due_date,
				available_until=available_until,
				is_published=is_published,
			)
			created.append(res["name"])
		except Exception as e:
			# revert only this item’s work; keep earlier successes
			frappe.db.rollback(save_point=sp)
			failed.append({
				"row": child_name,
				"error": frappe.get_traceback() if frappe.conf.developer_mode else str(e),
			})


	return {"created": created, "failed": failed}


@frappe.whitelist()
def duplicate_activity(lesson: str, activity_child_name: str) -> dict:
	if not lesson or not activity_child_name:
		frappe.throw(_("lesson and activity_child_name are required"))

	doc = frappe.get_doc("Lesson", lesson)
	row = next((r for r in (doc.get("activities") or []) if r.name == activity_child_name), None)
	if not row:
		frappe.throw(_("Activity row not found on this Lesson."))

	new_row = doc.append("activities", {})
	for f in ("activity_type", "title", "reading_content", "video_url", "external_link", "notes"):
		new_row.set(f, row.get(f))

	new_row.lesson_activity_order = _next_activity_order(lesson)

	doc.save()
	return {"name": new_row.name}



@frappe.whitelist()
def reorder_lesson_activities(lesson: str, activity_names):
	"""Set `lesson_activity_order` for child rows to 10,20,30... in the provided order."""
	if isinstance(activity_names, str):
		activity_names = frappe.parse_json(activity_names)
	if not isinstance(activity_names, (list, tuple)) or not activity_names:
		frappe.throw(_("activity_names must be a non-empty list."))

	rows = frappe.db.get_all(
		"Lesson Activity",
		filters={"parent": lesson, "name": ["in", activity_names]},
		fields=["name"],
		pluck="name",
	)
	if set(rows) != set(activity_names):
		missing = ", ".join(sorted(set(activity_names) - set(rows)))
		frappe.throw(_("Some activities do not belong to this lesson: {0}").format(missing))

	for idx, name in enumerate(activity_names):
		frappe.db.set_value(
			"Lesson Activity",
			name,
			"lesson_activity_order",
			(idx + 1) * _ACTIVITY_STEP,
			update_modified=False,
		)

	frappe.db.commit()
	return {"updated": len(activity_names), "order_step": _ACTIVITY_STEP}


@redis_cache(ttl=86400)
def get_ordered_activities(lesson: str) -> list[dict]:
	return frappe.get_all(
		"Lesson Activity",
		filters={"parent": lesson, "parenttype": "Lesson", "parentfield": "activities"},
		fields=[
			"name",
			"activity_type",
			"title",
			"lesson_activity_order",
			"video_url",
			"external_link",
		],
		order_by="lesson_activity_order asc, idx asc",
	)


def on_doctype_update():
	frappe.db.add_index("Lesson", ["learning_unit", "lesson_order"])
	frappe.db.add_index("Lesson Activity", ["parent", "lesson_activity_order"])
