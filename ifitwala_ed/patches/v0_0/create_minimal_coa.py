import frappe
from ifitwala_ed.accounting.coa_utils import create_coa_for_organization

def execute():
    frappe.reload_doc("accounting", "doctype", "account")
    frappe.reload_doc("accounting", "doctype", "chart_of_accounts_template")
    frappe.reload_doc("accounting", "doctype", "coa_template_row")
    
    # Reload Org Settings to ensure new fields are present
    frappe.reload_doc("setup", "doctype", "org_settings")

    orgs = frappe.get_all("Organization", filters={"archived": 0}, pluck="name")
    
    print(f"Found {len(orgs)} organizations to process.")
        
    for org in orgs:
        try:
            print(f"Processing Organization: {org}")
            result = create_coa_for_organization(org)
            print(f"  - Created: {result['created']}")
            print(f"  - Skipped: {result['skipped']}")
            print(f"  - Roots: {', '.join(result['root_accounts'])}")
        except Exception as e:
            print(f"  - Error processing {org}: {str(e)}")
            # Log error but continue with next org
            frappe.log_error(f"Error creating COA for {org}: {str(e)}", "Accounting Setup Patch")
