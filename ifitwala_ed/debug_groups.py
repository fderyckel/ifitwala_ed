
import frappe
from ifitwala_ed.api.student_attendance import fetch_portal_student_groups

def execute():
    try:
        groups = fetch_portal_student_groups()
        print(f"DEBUG: Found {len(groups)} groups")
        for g in groups[:5]:
            print(f" - {g.name}")
    except Exception as e:
        print(f"DEBUG: Error: {e}")
