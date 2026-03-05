# ifitwala_ed/scripts/backfill_student_allow_direct_creation.py

import frappe


def execute(dry_run: int = 0) -> dict:
    """Set Student.allow_direct_creation=1 for all current Student rows.

    Usage:
        bench --site <site> execute ifitwala_ed.scripts.backfill_student_allow_direct_creation.execute
        bench --site <site> execute ifitwala_ed.scripts.backfill_student_allow_direct_creation.execute --kwargs "{'dry_run': 1}"
    """
    if not frappe.db.table_exists("Student"):
        return {"ok": False, "reason": "Student table does not exist"}

    if not frappe.db.has_column("Student", "allow_direct_creation"):
        return {"ok": False, "reason": "Student.allow_direct_creation column does not exist"}

    total = frappe.db.count("Student")
    to_update = frappe.db.sql(
        """
        SELECT COUNT(*)
        FROM `tabStudent`
        WHERE IFNULL(allow_direct_creation, 0) <> 1
        """
    )[0][0]

    if int(dry_run or 0) == 1:
        return {"ok": True, "dry_run": True, "total_students": total, "to_update": to_update, "updated": 0}

    if to_update:
        frappe.db.sql(
            """
            UPDATE `tabStudent`
            SET allow_direct_creation = 1
            WHERE IFNULL(allow_direct_creation, 0) <> 1
            """
        )
        frappe.db.commit()

    return {
        "ok": True,
        "dry_run": False,
        "total_students": total,
        "to_update": to_update,
        "updated": to_update,
    }
