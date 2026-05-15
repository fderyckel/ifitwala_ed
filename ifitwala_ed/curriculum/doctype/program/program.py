# Copyright (c) 2024, Francois de Ryckel  and contributors
# For license information, please see license.txt

# ifitwala_ed/curriculum/doctype/program/program.py

import frappe
from frappe import _
from frappe.utils import cint
from frappe.utils.nestedset import NestedSet

FLOAT_EPS = 1e-6
PROGRAM_TREE_ROOT = "All Programs"


class Program(NestedSet):
    nsm_parent_field = "parent_program"

    def validate(self):
        self._validate_root_program_constraints()
        self._validate_parent_program_is_group()
        self._validate_group_nodes_keep_group_flag()

        # Keep existing validations
        self._validate_duplicate_course()
        self._validate_active_courses()
        self._validate_course_basket_groups()
        self._validate_website_publication()

        # New/updated validations for assessment model
        self._apply_default_colors_for_assessment_categories()
        self._validate_program_assessment_categories()

    def after_insert(self):
        self._sync_default_website_profiles()

    def on_update(self):
        NestedSet.on_update(self)
        if any(
            self.has_value_changed(fieldname)
            for fieldname in (
                "is_published",
                "program_slug",
                "program_image",
                "description",
                "program_overview",
                "program_aims",
            )
        ):
            self._sync_default_website_profiles()

    def _validate_root_program_constraints(self):
        if self.name != PROGRAM_TREE_ROOT:
            return

        if (self.parent_program or "").strip():
            frappe.throw(
                _("The root Program {program_name} cannot have a Parent Program.").format(
                    program_name=PROGRAM_TREE_ROOT
                )
            )

        if cint(self.archive) == 1:
            frappe.throw(
                _("The root Program {program_name} cannot be archived.").format(program_name=PROGRAM_TREE_ROOT)
            )

        if cint(self.is_group) != 1:
            frappe.throw(
                _("The root Program {program_name} must remain marked as Group.").format(program_name=PROGRAM_TREE_ROOT)
            )

    def _validate_parent_program_is_group(self):
        parent_program = (self.parent_program or "").strip()
        if not parent_program:
            return

        if self.name and parent_program == self.name:
            frappe.throw(_("A Program cannot be its own Parent Program."))

        parent_is_group = frappe.db.get_value("Program", parent_program, "is_group")
        if parent_is_group is None:
            frappe.throw(_("Parent Program {parent_program} was not found.").format(parent_program=parent_program))

        if cint(parent_is_group) != 1:
            frappe.throw(
                _(
                    "Parent Program {parent_program} must be marked as Group before it can own child programs. "
                    "Use Make Parent a Group or enable Group on that Program."
                ).format(parent_program=parent_program),
                frappe.ValidationError,
            )

    def _validate_group_nodes_keep_group_flag(self):
        if cint(self.is_group) == 1 or not self.name:
            return

        has_children = frappe.db.exists("Program", {"parent_program": self.name})
        if has_children:
            frappe.throw(
                _("Program {program_name} has child programs and must remain marked as Group.").format(
                    program_name=self.name
                ),
                frappe.ValidationError,
            )

    def _validate_duplicate_course(self):
        seen = set()
        for row in self.courses or []:
            if row.course in seen:
                frappe.throw(_("Course {course} entered twice").format(course=row.course))
            seen.add(row.course)

    def _validate_active_courses(self):
        # Batch fetch statuses to minimize DB calls
        names = [r.course for r in (self.courses or []) if r.course]
        if not names:
            return

        rows = frappe.get_all("Course", filters={"name": ["in", names]}, fields=["name", "status"])
        status_by_name = {r.name: (r.status or "") for r in rows}

        inactive = []
        for row in self.courses or []:
            if not row.course:
                continue
            st = status_by_name.get(row.course, "")
            if st != "Active":
                inactive.append((row.idx, row.course, st or "Unknown"))

        if inactive:
            lines = "\n".join([f"Row {idx}: {name} (status: {st})" for idx, name, st in inactive])
            frappe.throw(_("Only Active Courses can be added:\n{courses}").format(courses=lines))

    def _validate_website_publication(self):
        if cint(self.is_published) != 1:
            return
        if cint(self.archive) == 1:
            frappe.throw(
                _("Archived programs cannot be published."),
                frappe.ValidationError,
            )
        if not (self.program_slug or "").strip():
            from ifitwala_ed.website.bootstrap import _next_available_program_slug

            self.program_slug = _next_available_program_slug(
                self.program_name or self.name,
                program_name=self.name or self.program_name,
            )

    def _sync_default_website_profiles(self):
        if cint(self.is_published) != 1 or cint(self.archive) == 1:
            return

        from ifitwala_ed.website.bootstrap import ensure_default_program_website_profiles

        ensure_default_program_website_profiles(program_name=self.name)

    def _validate_course_basket_groups(self):
        valid_courses = {(row.course or "").strip() for row in (self.courses or []) if (row.course or "").strip()}
        if not getattr(self, "course_basket_groups", None):
            return

        seen = set()
        for idx, row in enumerate(self.course_basket_groups or [], start=1):
            course = (row.course or "").strip()
            basket_group = (row.basket_group or "").strip()
            if not course:
                frappe.throw(
                    _("Enrollment basket membership row {row_number}: Course is required.").format(row_number=idx)
                )
            if course not in valid_courses:
                frappe.throw(
                    _(
                        "Enrollment basket membership row {row_number}: Course {course} is not present in Program Courses."
                    ).format(
                        row_number=idx,
                        course=course,
                    )
                )
            if not basket_group:
                frappe.throw(
                    _("Enrollment basket membership row {row_number}: Basket Group (Enrollment) is required.").format(
                        row_number=idx
                    )
                )

            key = (course, basket_group)
            if key in seen:
                frappe.throw(
                    _(
                        "Enrollment basket membership row {row_number}: duplicate mapping for {course} -> {basket_group}."
                    ).format(
                        row_number=idx,
                        course=course,
                        basket_group=basket_group,
                    )
                )
            seen.add(key)

    # ──────────────────────────────────────────────────────────────────────────────
    # Assessment Categories (Program Assessment Category child)
    # We ALLOW multiple schemes together (points/binary/criteria/feedback).
    # We ONLY enforce weight math when Points is enabled.
    # ──────────────────────────────────────────────────────────────────────────────

    def _apply_default_colors_for_assessment_categories(self):
        """For any row missing color_override, pull the color from the master
        Assessment Category (field: assessment_category_color) in one batch.
        """
        rows = self.get("assessment_categories") or []
        missing = [
            r.assessment_category.strip()
            for r in rows
            if getattr(r, "assessment_category", None) and not getattr(r, "color_override", None)
        ]
        if not missing:
            return

        # Batch fetch colors from master doctype
        masters = frappe.get_all(
            "Assessment Category",
            filters={"name": ["in", list(set(missing))]},
            fields=["name", "assessment_category_color"],
        )
        color_map = {m.name: (m.assessment_category_color or "") for m in masters}

        for r in rows:
            cat = (r.assessment_category or "").strip()
            if cat and not r.color_override:
                default_color = color_map.get(cat, "")
                if default_color:
                    r.color_override = default_color

    def _validate_program_assessment_categories(self):
        rows = _get_effective_assessment_category_rows(self)

        points_on = cint(self.points) == 1
        # criteria_on  = cint(self.criteria) == 1  # allowed concurrently
        # binary_on    = cint(self.binary)   == 1  # allowed concurrently
        # feedback_on  = (cint(self.observations) == 1) if your flag becomes 'feedback'

        # Per-row checks + duplicate guard
        seen = set()
        active_total = 0.0
        neg_rows, over_rows, dup_rows = [], [], []

        for r in rows:
            cat = (r.assessment_category or "").strip()
            weight = float(r.default_weight or 0)
            active = cint(r.active) == 1

            # duplicate category guard
            if cat:
                if cat in seen:
                    dup_rows.append((r.idx, cat))
                else:
                    seen.add(cat)

            # 0..100 guard per row (weight field itself should be sane)
            if weight < 0 - FLOAT_EPS:
                neg_rows.append(r.idx)
            if weight > 100 + FLOAT_EPS:
                over_rows.append(r.idx)

            # Only meaningful when Points is enabled, but we sum now;
            # enforcement happens below.
            if active:
                active_total += weight

        if dup_rows:
            lines = "\n".join([f"Row {idx}: {cat}" for idx, cat in dup_rows])
            frappe.throw(_("Duplicate Assessment Categories are not allowed:\n{categories}").format(categories=lines))
        if neg_rows:
            frappe.throw(
                _("Default Weight cannot be negative (rows: {row_numbers}).").format(
                    row_numbers=", ".join(map(str, neg_rows))
                )
            )
        if over_rows:
            frappe.throw(
                _("Default Weight cannot exceed 100 (rows: {row_numbers}).").format(
                    row_numbers=", ".join(map(str, over_rows))
                )
            )

        # Weight math ONLY enforced if Points is enabled
        if points_on:
            has_active = any(cint(r.active) == 1 for r in rows)
            if not has_active:
                frappe.throw(_("With Points enabled, add at least one active Assessment Category with a weight."))

            if active_total > 100.0 + 0.0001:
                frappe.throw(
                    _(
                        "For Points, the total of active category weights must not exceed 100 (current total: {total_weight:.2f})."
                    ).format(total_weight=active_total)
                )

            # If you want exact 100 when publishing later, enforce in on_submit or before_publish hook.
            # Example (not enabled here):
            # if cint(self.is_published) and abs(active_total - 100.0) > 0.0001:
            #     frappe.throw(_("Published Programs using Points must total exactly 100 (current total: {0:.2f}).").format(active_total))


def _as_category_row(row) -> frappe._dict:
    return frappe._dict(
        {
            "assessment_category": getattr(row, "assessment_category", None),
            "default_weight": getattr(row, "default_weight", None),
            "color_override": getattr(row, "color_override", None),
            "active": getattr(row, "active", 0),
            "idx": getattr(row, "idx", None),
        }
    )


def _resolve_effective_assessment_category_source(doc: Program) -> tuple[str | None, list[frappe._dict]]:
    """
    Return the nearest Program whose assessment_categories should apply.

    Local rows always win. If the local child table is empty, walk the parent_program
    chain until the nearest ancestor with rows is found.
    """
    current = doc
    visited = set()

    while current:
        current_key = current.name or f"__unsaved__:{id(current)}"
        if current_key in visited:
            break
        visited.add(current_key)

        rows = [
            _as_category_row(row) for row in (current.get("assessment_categories") or []) if row.assessment_category
        ]
        if rows:
            return current.name, rows

        parent_name = (current.parent_program or "").strip()
        if not parent_name:
            break
        current = frappe.get_doc("Program", parent_name)

    return None, []


def _get_effective_assessment_category_rows(doc: Program) -> list[frappe._dict]:
    _source_program, rows = _resolve_effective_assessment_category_source(doc)
    return rows


@frappe.whitelist()
def get_effective_assessment_categories(program: str):
    if not program:
        frappe.throw(_("Program is required."))

    doc = frappe.get_doc("Program", program)
    source_program, rows = _resolve_effective_assessment_category_source(doc)
    return {
        "source_program": source_program,
        "rows": rows,
        "inherited": bool(source_program and source_program != doc.name),
    }


@frappe.whitelist()
def inherit_assessment_categories(program: str, overwrite: int = 1):
    """Copy parent's Program Assessment Category rows into this Program (overwrites by default)."""
    if not program:
        frappe.throw(_("Program is required."))

    doc = frappe.get_doc("Program", program)

    if not doc.parent_program:
        frappe.throw(_("This Program has no Parent Program set."))

    parent = frappe.get_doc("Program", doc.parent_program)
    parent_rows = parent.get("assessment_categories") or []  # Program Assessment Category
    if not parent_rows:
        frappe.throw(
            _("Parent Program <b>{program_name}</b> has no Program Assessment Categories to inherit.").format(
                program_name=parent.name
            )
        )

    # De-dup by Assessment Category link while copying
    seen = set()
    clean_rows = []
    for r in parent_rows:
        cat = (r.assessment_category or "").strip()
        if not cat or cat in seen:
            continue
        seen.add(cat)
        clean_rows.append(
            {
                "assessment_category": r.assessment_category,
                "default_weight": r.default_weight,
                "color_override": r.color_override,
                "active": int(r.active or 0),
            }
        )

    if not clean_rows:
        frappe.throw(_("Nothing to import after cleaning duplicates / empty rows."))

    # Overwrite current child table
    if int(overwrite or 0):
        doc.set("assessment_categories", [])

    for row in clean_rows:
        doc.append("assessment_categories", row)

    doc.save(ignore_permissions=False)

    return {"parent": parent.name, "added": len(clean_rows), "total": len(doc.get("assessment_categories") or [])}


@frappe.whitelist()
def make_program_group(program: str):
    if not program:
        frappe.throw(_("Program is required."))

    doc = frappe.get_doc("Program", program)
    doc.check_permission("write")

    if cint(doc.is_group) == 1:
        return {"program": doc.name, "changed": False}

    doc.is_group = 1
    doc.save()
    return {"program": doc.name, "changed": True}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def program_parent_query(doctype, txt, searchfield, start, page_len, filters):
    raw_filters = filters or {}
    if isinstance(raw_filters, str):
        try:
            raw_filters = frappe.parse_json(raw_filters) or {}
        except Exception:
            raw_filters = {}
    if not isinstance(raw_filters, dict):
        raw_filters = {}

    current_program = ((raw_filters or {}).get("current_program") or "").strip()
    conditions = []
    params = []

    search_txt = (txt or "").strip()
    if search_txt:
        like_txt = f"%{search_txt}%"
        conditions.append("(name like %s or program_name like %s)")
        params.extend([like_txt, like_txt])

    if current_program:
        bounds = frappe.db.get_value("Program", current_program, ["lft", "rgt"], as_dict=True)
        if bounds and bounds.get("lft") is not None and bounds.get("rgt") is not None:
            conditions.append("not (lft >= %s and rgt <= %s)")
            params.extend([bounds["lft"], bounds["rgt"]])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""
        SELECT name, program_name
        FROM `tabProgram`
        {where_clause}
        ORDER BY lft ASC, program_name ASC, name ASC
        LIMIT %s, %s
    """
    params.extend([int(start or 0), int(page_len or 20)])
    return frappe.db.sql(sql, params)
