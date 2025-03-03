import frappe

@frappe.whitelist()
def get_students(group_id, start=0, page_length=25):
    """
    Returns a JSON list of Student records (25 at a time) for the given group_id.
    Only permitted if the current user is listed in the Student Group Instructor table.
    """
    # Permission check
    if not user_is_instructor_for_group(frappe.session.user, group_id):
        frappe.throw("Not permitted", frappe.PermissionError)

    # Fetch from child table "Student Group Student"
    # We'll order by 'idx' so it respects the row order in the child table
    student_links = frappe.db.get_list(
        "Student Group Student",
        filters={"parent": group_id},
        fields=["student"],
        start=start,
        page_length=page_length,
        order_by="idx asc"
    )

    # For each child, fetch minimal fields from the "Student" doctype
    results = []
    for row in student_links:
        doc = frappe.db.get_value(
            "Student",
            row.student,
            [
                "name",
                "student_full_name",
                "student_preferred_name",
                "student_date_of_birth",
                "student_image"
            ],
            as_dict=True
        )
        if doc:
            results.append(doc)

    return results


def user_is_instructor_for_group(user, group_id):
    """
    Checks if the given system user is listed as 'user_id' in any row of
    the Student Group Instructor child table for this student group.
    """
    return frappe.db.exists(
        "Student Group Instructor",
        {
            "parent": group_id,
            "user_id": user
        }
    )
