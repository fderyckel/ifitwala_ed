import frappe
from frappe.model.document import Document
from frappe import _

class Account(Document):
    def validate(self):
        self.validate_organization()
        self.validate_root_type()
        self.set_report_type()
        self.validate_parent()
        self.validate_account_type()
        self.validate_group()
        
    def set_report_type(self):
        if self.root_type in ["Asset", "Liability", "Equity"]:
            self.report_type = "Balance Sheet"
        elif self.root_type in ["Income", "Expense"]:
             self.report_type = "Profit and Loss"
        
    def validate_organization(self):
        if not self.organization:
            frappe.throw(_("Organization is required"))

    def validate_root_type(self):
        if not self.root_type:
            frappe.throw(_("Root Type is required"))

    def validate_parent(self):
        if self.parent_account:
            parent = frappe.get_doc("Account", self.parent_account)
            
            # Parent must exist (implicit by get_doc, but good check)
            if not parent:
                frappe.throw(_("Parent account not found"))
                
            # Parent must belong to same organization
            if parent.organization != self.organization:
                frappe.throw(_("Parent account must belong to the same organization"))
                
            # Child root_type must equal parent root_type
            if parent.root_type != self.root_type:
                frappe.throw(_("Root Type must be the same as parent account"))
                
            # Prevent circular parenting (NestedSet checks strictly, but we catch self-parent here)
            if self.name and parent.name == self.name:
                frappe.throw(_("You cannot be your own parent"))
                
            # Note: Full circular ancestor check is handled by NestedSet's validate_one_root and recursion checks.


    def validate_account_type(self):
        if not self.account_type:
            return

        # Bank/Cash/Receivable -> Asset
        if self.account_type in ["Bank", "Cash", "Receivable"]:
            if self.root_type != "Asset":
                frappe.throw(_("Account Type '{0}' must have Root Type 'Asset'").format(self.account_type))
                
        # Tax -> Liability (Phase 0)
        if self.account_type == "Tax":
            if self.root_type != "Liability":
                frappe.throw(_("Account Type 'Tax' must have Root Type 'Liability'"))
                
    def validate_group(self):
        # If is_group == 1, treat as non-postable later. 
        # Step 1 just stores it.
        pass
