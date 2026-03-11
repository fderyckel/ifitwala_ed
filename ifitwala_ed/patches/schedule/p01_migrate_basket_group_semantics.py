# ifitwala_ed/patches/schedule/p01_migrate_basket_group_semantics.py

import frappe


def execute():
    if not frappe.db.table_exists("Basket Group"):
        return

    _seed_basket_groups()
    _backfill_program_course_basket_groups()
    _backfill_offering_course_basket_groups()
    _backfill_enrollment_rule_basket_group()
    _backfill_applicant_enrollment_plan_course_snapshots()
    _backfill_request_course_snapshots()
    _backfill_enrollment_course_snapshots()


def _seed_basket_groups():
    names = set()

    if frappe.db.table_exists("Program Course") and frappe.db.has_column("Program Course", "category"):
        rows = frappe.db.sql(
            """
            SELECT DISTINCT category
            FROM `tabProgram Course`
            WHERE IFNULL(category, '') != ''
            """,
            as_list=True,
        )
        names.update((row[0] or "").strip() for row in rows if row and (row[0] or "").strip())

    if frappe.db.table_exists("Program Offering Course") and frappe.db.has_column(
        "Program Offering Course", "elective_group"
    ):
        rows = frappe.db.sql(
            """
            SELECT DISTINCT elective_group
            FROM `tabProgram Offering Course`
            WHERE IFNULL(elective_group, '') != ''
            """,
            as_list=True,
        )
        names.update((row[0] or "").strip() for row in rows if row and (row[0] or "").strip())

    if frappe.db.table_exists("Program Offering Enrollment Rule") and frappe.db.has_column(
        "Program Offering Enrollment Rule", "course_group"
    ):
        rows = frappe.db.sql(
            """
            SELECT DISTINCT course_group
            FROM `tabProgram Offering Enrollment Rule`
            WHERE IFNULL(course_group, '') != ''
            """,
            as_list=True,
        )
        names.update((row[0] or "").strip() for row in rows if row and (row[0] or "").strip())

    for name in sorted(names):
        if frappe.db.exists("Basket Group", name):
            continue
        frappe.get_doc({"doctype": "Basket Group", "basket_group_name": name}).insert(ignore_permissions=True)


def _insert_child_row(doctype: str, parent: str, parenttype: str, parentfield: str, payload: dict):
    filters = {"parent": parent, "parenttype": parenttype, "parentfield": parentfield}
    filters.update(payload)
    if frappe.db.exists(doctype, filters):
        return

    doc = frappe.get_doc(
        {"doctype": doctype, "parent": parent, "parenttype": parenttype, "parentfield": parentfield, **payload}
    )
    doc.insert(ignore_permissions=True)


def _backfill_program_course_basket_groups():
    if not frappe.db.table_exists("Program Course Basket Group"):
        return
    if not frappe.db.table_exists("Program Course") or not frappe.db.has_column("Program Course", "category"):
        return

    rows = frappe.db.sql(
        """
        SELECT parent, course, category
        FROM `tabProgram Course`
        WHERE IFNULL(course, '') != ''
          AND IFNULL(category, '') != ''
        ORDER BY parent, idx
        """,
        as_dict=True,
    )
    for row in rows:
        _insert_child_row(
            "Program Course Basket Group",
            row["parent"],
            "Program",
            "course_basket_groups",
            {"course": row["course"], "basket_group": row["category"]},
        )


def _backfill_offering_course_basket_groups():
    if not frappe.db.table_exists("Program Offering Course Basket Group"):
        return
    if not frappe.db.table_exists("Program Offering Course") or not frappe.db.has_column(
        "Program Offering Course", "elective_group"
    ):
        return

    rows = frappe.db.sql(
        """
        SELECT parent, course, elective_group
        FROM `tabProgram Offering Course`
        WHERE IFNULL(course, '') != ''
          AND IFNULL(elective_group, '') != ''
        ORDER BY parent, idx
        """,
        as_dict=True,
    )
    for row in rows:
        _insert_child_row(
            "Program Offering Course Basket Group",
            row["parent"],
            "Program Offering",
            "offering_course_basket_groups",
            {"course": row["course"], "basket_group": row["elective_group"]},
        )


def _backfill_enrollment_rule_basket_group():
    if not frappe.db.table_exists("Program Offering Enrollment Rule"):
        return
    if not frappe.db.has_column("Program Offering Enrollment Rule", "basket_group"):
        return
    if not frappe.db.has_column("Program Offering Enrollment Rule", "course_group"):
        return

    frappe.db.sql(
        """
        UPDATE `tabProgram Offering Enrollment Rule`
        SET basket_group = course_group
        WHERE IFNULL(basket_group, '') = ''
          AND IFNULL(course_group, '') != ''
        """
    )


def _offering_legacy_semantics_map() -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}

    if not frappe.db.table_exists("Program Offering Course"):
        return out

    fields = ["parent", "course", "required"]
    if frappe.db.has_column("Program Offering Course", "elective_group"):
        fields.append("elective_group")

    rows = frappe.get_all(
        "Program Offering Course",
        fields=fields,
        order_by="parent asc, idx asc",
        limit_page_length=100000,
    )
    for row in rows:
        parent = (row.get("parent") or "").strip()
        course = (row.get("course") or "").strip()
        if not parent or not course:
            continue
        key = (parent, course)
        current = out.get(key)
        if not current:
            current = {"required": 1 if row.get("required") else 0, "applied_basket_group": ""}
            out[key] = current
        else:
            current["required"] = 1 if current.get("required") or row.get("required") else 0

        legacy_group = (row.get("elective_group") or "").strip()
        if legacy_group and not current.get("applied_basket_group"):
            current["applied_basket_group"] = legacy_group

    return out


def _backfill_applicant_enrollment_plan_course_snapshots():
    if not frappe.db.table_exists("Applicant Enrollment Plan Course"):
        return
    if not frappe.db.has_column("Applicant Enrollment Plan Course", "required"):
        return

    offering_map = _offering_legacy_semantics_map()
    plans = frappe.get_all(
        "Applicant Enrollment Plan",
        fields=["name", "program_offering"],
        limit_page_length=100000,
    )
    for plan in plans:
        parent = (plan.get("name") or "").strip()
        program_offering = (plan.get("program_offering") or "").strip()
        if not parent or not program_offering:
            continue
        rows = frappe.get_all(
            "Applicant Enrollment Plan Course",
            filters={"parent": parent, "parenttype": "Applicant Enrollment Plan"},
            fields=["name", "course", "required", "applied_basket_group"],
            limit_page_length=5000,
        )
        for row in rows:
            key = (program_offering, (row.get("course") or "").strip())
            semantics = offering_map.get(key) or {}
            updates = {}
            if semantics and not int(row.get("required") or 0) and semantics.get("required"):
                updates["required"] = semantics["required"]
            if (
                semantics
                and not (row.get("applied_basket_group") or "").strip()
                and semantics.get("applied_basket_group")
            ):
                updates["applied_basket_group"] = semantics["applied_basket_group"]
            if updates:
                frappe.db.set_value("Applicant Enrollment Plan Course", row["name"], updates, update_modified=False)


def _backfill_request_course_snapshots():
    if not frappe.db.table_exists("Program Enrollment Request Course"):
        return
    if not frappe.db.has_column("Program Enrollment Request Course", "required"):
        return

    offering_map = _offering_legacy_semantics_map()
    requests = frappe.get_all(
        "Program Enrollment Request",
        fields=["name", "program_offering"],
        limit_page_length=100000,
    )
    for request in requests:
        parent = (request.get("name") or "").strip()
        program_offering = (request.get("program_offering") or "").strip()
        if not parent or not program_offering:
            continue
        rows = frappe.get_all(
            "Program Enrollment Request Course",
            filters={"parent": parent, "parenttype": "Program Enrollment Request"},
            fields=["name", "course", "required", "applied_basket_group"],
            limit_page_length=5000,
        )
        for row in rows:
            key = (program_offering, (row.get("course") or "").strip())
            semantics = offering_map.get(key) or {}
            updates = {}
            if semantics and not int(row.get("required") or 0) and semantics.get("required"):
                updates["required"] = semantics["required"]
            if (
                semantics
                and not (row.get("applied_basket_group") or "").strip()
                and semantics.get("applied_basket_group")
            ):
                updates["applied_basket_group"] = semantics["applied_basket_group"]
            if updates:
                frappe.db.set_value("Program Enrollment Request Course", row["name"], updates, update_modified=False)


def _backfill_enrollment_course_snapshots():
    if not frappe.db.table_exists("Program Enrollment Course"):
        return
    if not frappe.db.has_column("Program Enrollment Course", "required"):
        return

    offering_map = _offering_legacy_semantics_map()
    enrollments = frappe.get_all(
        "Program Enrollment",
        fields=["name", "program_offering", "program_enrollment_request"],
        limit_page_length=100000,
    )
    request_rows = {}
    if frappe.db.table_exists("Program Enrollment Request Course"):
        rows = frappe.get_all(
            "Program Enrollment Request Course",
            fields=["parent", "course", "required", "applied_basket_group"],
            limit_page_length=100000,
        )
        for row in rows:
            request_rows[(row.get("parent"), row.get("course"))] = {
                "required": 1 if row.get("required") else 0,
                "credited_basket_group": (row.get("applied_basket_group") or "").strip(),
            }

    for enrollment in enrollments:
        parent = (enrollment.get("name") or "").strip()
        program_offering = (enrollment.get("program_offering") or "").strip()
        request_name = (enrollment.get("program_enrollment_request") or "").strip()
        if not parent or not program_offering:
            continue
        rows = frappe.get_all(
            "Program Enrollment Course",
            filters={"parent": parent, "parenttype": "Program Enrollment"},
            fields=["name", "course", "required", "credited_basket_group"],
            limit_page_length=5000,
        )
        for row in rows:
            request_semantics = request_rows.get((request_name, row.get("course"))) if request_name else None
            offering_semantics = offering_map.get((program_offering, (row.get("course") or "").strip())) or {}
            updates = {}
            if request_semantics:
                if not int(row.get("required") or 0) and request_semantics.get("required"):
                    updates["required"] = request_semantics["required"]
                if not (row.get("credited_basket_group") or "").strip() and request_semantics.get(
                    "credited_basket_group"
                ):
                    updates["credited_basket_group"] = request_semantics["credited_basket_group"]
            else:
                if offering_semantics and not int(row.get("required") or 0) and offering_semantics.get("required"):
                    updates["required"] = offering_semantics["required"]
                if (
                    offering_semantics
                    and not (row.get("credited_basket_group") or "").strip()
                    and offering_semantics.get("applied_basket_group")
                ):
                    updates["credited_basket_group"] = offering_semantics["applied_basket_group"]
            if updates:
                frappe.db.set_value("Program Enrollment Course", row["name"], updates, update_modified=False)
