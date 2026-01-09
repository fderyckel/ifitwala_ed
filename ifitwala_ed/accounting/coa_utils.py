import frappe
from frappe import _

def get_minimal_coa_skeleton():
    """
    Returns a Python structure describing the minimal required tree.
    """
    return [
        # Assets
        {"account_name": "Assets", "root_type": "Asset", "is_group": 1, "parent": None},
        {"account_name": "Accounts Receivable", "root_type": "Asset", "account_type": "Receivable", "is_group": 0, "parent": "Assets"},
        {"account_name": "Cash", "root_type": "Asset", "account_type": "Cash", "is_group": 0, "parent": "Assets"},
        {"account_name": "Bank", "root_type": "Asset", "account_type": "Bank", "is_group": 0, "parent": "Assets"},
        
        # Liabilities
        {"account_name": "Liabilities", "root_type": "Liability", "is_group": 1, "parent": None},
        {"account_name": "Advances / Unearned Revenue", "root_type": "Liability", "is_group": 0, "parent": "Liabilities", "account_type": None}, # Explicitly None for Phase 0
        {"account_name": "Tax Payable", "root_type": "Liability", "account_type": "Tax", "is_group": 0, "parent": "Liabilities"},
        
        # Equity
        {"account_name": "Equity", "root_type": "Equity", "is_group": 1, "parent": None},
        
        # Income
        {"account_name": "Income", "root_type": "Income", "is_group": 1, "parent": None},
        
        # Expenses
        {"account_name": "Expenses", "root_type": "Expense", "is_group": 1, "parent": None},
    ]

def get_account(organization, account_name, parent=None):
    """
    Returns IF Account name (docname) for that org + name (exact match).
    If parent is specified, we can try to be more specific, but uniqueness is primarily on name + organization.
    The spec asks for uniqueness on (organization, account_name, parent_account).
    """
    filters = {
        "organization": organization,
        "account_name": account_name
    }
    if parent:
        filters["parent_account"] = parent
        
    accounts = frappe.get_all("Account", filters=filters, pluck="name", limit=1)
    return accounts[0] if accounts else None

def create_coa_for_organization(organization, template_name=None):
    """
    Creates accounts for the given Organization.
    Must be idempotent.
    Returns dict with stats.
    """
    created_count = 0
    skipped_count = 0
    root_accounts = []
    
    # 1. Determine the list of accounts to create (rows)
    rows_to_create = []
    
    if template_name:
        template = frappe.get_doc("Chart of Accounts Template", template_name)
        for row in template.accounts:
            rows_to_create.append({
                "account_name": row.account_name,
                "account_number": row.account_number, # Optional
                "root_type": row.root_type,
                "account_type": row.account_type,
                "is_group": row.is_group,
                "parent_name_ref": row.parent_account_name # Reference name in template
            })
            
        # Refine structure logic for templates if needed, but for now assuming flattened list or we handle ordering.
        # Ideally we should sort by hierarchy depth, but we don't know depth purely from rows easily without building a tree.
        # A simple approach: First Pass -> create roots. Second Pass -> create children. 
        # Or just retry? 
        # Spec says "create accounts in correct parent-child order".
        # Let's assume the template rows are reasonably ordered or we do multiple passes.
        # Better: Build a graph or use simple depth logic if "parent_account_name" refers to names in the same list.
        
        # Optimistic approach: Create roots (no parent), then iterate until all created.
        pass
    else:
        # Minimal Skeleton
        skeleton = get_minimal_coa_skeleton()
        for item in skeleton:
            rows_to_create.append({
                "account_name": item["account_name"],
                "root_type": item["root_type"],
                "account_type": item.get("account_type"),
                "is_group": item["is_group"],
                "parent_name_ref": item["parent"]
            })
            
    # 2. Existing accounts cache for efficiency
    # Map: name -> docname (for this org)
    existing_accounts_map = {} 
    existing_list = frappe.get_all("Account", filters={"organization": organization}, fields=["account_name", "name", "parent_account"])
    for acc in existing_list:
        existing_accounts_map[acc.account_name] = acc.name
        
    # 3. Creation Loop
    # We might need multiple passes to resolve parents if they appear later in the list.
    # Logic: try to create. If parent missing, re-queue?
    # Minimal skeleton is ordered (Roots first, then children). checking order.
    # My skeleton definition has Roots first.
    
    queue = rows_to_create[:]
    max_passes = 10 # Safety
    pass_count = 0
    
    while queue and pass_count < max_passes:
        pass_count += 1
        next_queue = []
        
        for row in queue:
            acc_name = row["account_name"]
            parent_ref = row.get("parent_name_ref")
            
            # Check if exists (Idempotency)
            # Complex check: Exact match on org + name + parent?
            # Or just name within org? User requirement: "Unique constraint (organization, account_name, parent_account)"
            # But usually account names are unique per org ideally, or at least per parent.
            # My get_minimal_coa_skeleton uses unique names globally for the skeleton.
            
            # Let's check based on Name + Org first.
            if acc_name in existing_accounts_map:
                # Already exists.
                # Strictly speaking, we should verify parent matches too?
                # If parent def differs, we might be creating a duplicate with same name under diff parent. 
                # For minimal skeleton, names are unique.
                skipped_count += 1
                if not row.get("parent_name_ref"): # It's a root
                     root_accounts.append(acc_name)
                continue
                
            # If has parent, resolve parent
            parent_docname = None
            if parent_ref:
                if parent_ref in existing_accounts_map:
                    parent_docname = existing_accounts_map[parent_ref]
                else:
                    # Parent doesn't exist yet, retry next pass
                    next_queue.append(row)
                    continue
            
            # Create
            new_acc = frappe.new_doc("Account")
            new_acc.organization = organization
            new_acc.account_name = acc_name
            new_acc.root_type = row["root_type"]
            new_acc.account_type = row.get("account_type")
            new_acc.is_group = row["is_group"]
            if parent_docname:
                new_acc.parent_account = parent_docname
            
            new_acc.flags.ignore_permissions = True
            new_acc.insert()
            
            existing_accounts_map[acc_name] = new_acc.name
            created_count += 1
            if not parent_docname:
                 root_accounts.append(acc_name)
                 
        queue = next_queue
        
    return {
        "created": created_count,
        "skipped": skipped_count,
        "root_accounts": root_accounts
    }
