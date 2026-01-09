import frappe
from ifitwala_ed.accounting.account_holder_utils import get_school_organization

def execute():
    frappe.reload_doc("accounting", "doctype", "account_holder")
    frappe.reload_doc("students", "doctype", "student")
    
    students = frappe.get_all(
        "Student",
        fields=[
            "name",
            "student_first_name",
            "student_middle_name",
            "student_last_name",
            "anchor_school",
            "account_holder",
        ],
    )
    
    print(f"Processing {len(students)} students for Account Holder migration...")
    
    for student in students:
        if student.account_holder:
            continue
            
        if not student.anchor_school:
            print(f"Skipping student {student.name}: No Anchor School")
            continue
            
        try:
            org = get_school_organization(student.anchor_school)
            if not org:
                print(f"Skipping student {student.name}: No Organization for school {student.anchor_school}")
                continue
                
            # Check for Guardians - Deterministic Sort
            guardians = frappe.get_all("Student Guardian", filters={"parent": student.name}, fields=["guardian", "idx"], order_by="idx asc, creation asc")
            
            holder_name = ""
            holder_type = ""
            
            if guardians:
                # Use first guardian
                guardian_id = guardians[0].guardian
                guardian_name = frappe.db.get_value("Guardian", guardian_id, "guardian_name")
                holder_name = guardian_name
                holder_type = "Individual"
            else:
                # Use Student Name
                full_name = " ".join(
                    filter(
                        None,
                        [
                            student.student_first_name,
                            student.student_middle_name,
                            student.student_last_name,
                        ],
                    )
                )
                holder_name = f"{full_name} (Payer)"
                holder_type = "Student (Adult)"
                
            # Check if Account Holder exists (Idempotencyish Re-use)
            # Match on Name + Org + Type
            existing = frappe.get_value("Account Holder", {
                "organization": org, 
                "account_holder_name": holder_name,
                "account_holder_type": holder_type
            }, "name")
            
            if existing:
                holder_docname = existing
            else:
                # Create
                ah = frappe.new_doc("Account Holder")
                ah.organization = org
                ah.account_holder_name = holder_name
                ah.account_holder_type = holder_type
                ah.status = "Active"
                ah.insert()
                holder_docname = ah.name
                
            # Link to Student
            # Use save() to trigger validation (Step 3 Requirement)
            student_doc = frappe.get_doc("Student", student.name)
            student_doc.account_holder = holder_docname
            student_doc.save(ignore_permissions=True)
            
            print(f"Assigned Account Holder {holder_docname} to Student {student.name}")
            
        except Exception as e:
            print(f"Error processing student {student.name}: {e}")
            frappe.log_error(f"Error migrating student {student.name}: {e}", "Account Holder Migration")
