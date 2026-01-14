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

def get_account_by_name(organization, account_name, parent=None):
    """
    Returns IF Account name (docname) for that org + name.
    If parent is specified, we check for exact parent match.
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
    root_accounts = [] # List of docnames
    
    # 1. Determine the list of accounts to create (rows)
    rows_to_create = []
    
    if template_name:
        template = frappe.get_doc("Chart of Accounts Template", template_name)
        for row in template.accounts:
            rows_to_create.append({
                "account_name": row.account_name,
                "account_number": row.account_number,
                "root_type": row.root_type,
                "account_type": row.account_type,
                "is_group": row.is_group,
                "parent_name_ref": row.parent_account_name # Reference name in template
            })
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
    # Key: (account_name, parent_docname) -> docname
    # Root accounts key: (account_name, None)
    existing_accounts_map = {} 
    
    # Also keep a map of account_name -> docname (list) for loosely guessing parent checking if strict check fails?
    # No, strictly follow (name, parent).
    
    existing_list = frappe.get_all("Account", filters={"organization": organization}, fields=["account_name", "name", "parent_account", "root_type"])
    for acc in existing_list:
        key = (acc.account_name, acc.parent_account)
        existing_accounts_map[key] = acc.name
        
        if not acc.parent_account:
            root_accounts.append(acc.name)
        
    # 3. Creation Loop (Multi-pass)
    queue = rows_to_create[:]
    max_passes = 15 # Allow deeper trees
    pass_count = 0
    
    while queue and pass_count < max_passes:
        pass_count += 1
        next_queue = []
        progress_made = False
        
        for row in queue:
            acc_name = row["account_name"]
            parent_ref_name = row.get("parent_name_ref")
            
            # Resolve Parent Docname
            parent_docname = None
            if parent_ref_name:
                # We need to find the docname of the parent in *this* organization.
                # Since parent ref is just a name string (e.g. "Assets"), we look it up.
                # Issue: What if multiple "Assets"? (Unlikely for roots, but possible for sub-groups).
                # Assumption: Template structure implies unique names at least for intended parents within the scope.
                # We scan existing_accounts_map for a match on name.
                
                # Heuristic: Find any account in this org with that name.
                # Ideally, we should know the structure, but here we flat search.
                found_parent = None
                for (ex_name, ex_parent), ex_docname in existing_accounts_map.items():
                    if ex_name == parent_ref_name:
                        found_parent = ex_docname
                        break
                
                if found_parent:
                    parent_docname = found_parent
                else:
                    # Parent not created yet, or missing. Retry next pass.
                    next_queue.append(row)
                    continue
            
            # IDEMPOTENCY CHECK
            # Check if (acc_name, parent_docname) exists
            key = (acc_name, parent_docname)
            if key in existing_accounts_map:
                skipped_count += 1
                if not parent_docname and existing_accounts_map[key] not in root_accounts:
                     root_accounts.append(existing_accounts_map[key])
                continue
            
            # Create
            new_acc = frappe.new_doc("Account")
            new_acc.organization = organization
            new_acc.account_name = acc_name
            new_acc.account_number = row.get("account_number")
            new_acc.root_type = row["root_type"]
            new_acc.account_type = row.get("account_type")
            new_acc.is_group = row["is_group"]
            if parent_docname:
                new_acc.parent_account = parent_docname
            
            # Auto-set report_type handled by controller, but good to be explicit if we wanted.
            # Controller handles it.
            
            new_acc.flags.ignore_permissions = True
            new_acc.insert()
            
            # Update cache
            existing_accounts_map[key] = new_acc.name
            created_count += 1
            progress_made = True
            
            if not parent_docname:
                 root_accounts.append(new_acc.name)
                 
        if not progress_made and next_queue:
            # We are stuck. Parents for remaining items don't exist.
            missing_parents = {r.get('parent_name_ref') for r in next_queue}
            frappe.throw(_("Could not resolve parents for accounts: {0}. Missing parents: {1}").format(
                ", ".join([r["account_name"] for r in next_queue]),
                ", ".join(missing_parents)
            ))
            
        queue = next_queue
        
    ensure_accounts_settings(organization)

    return {
        "created": created_count,
        "skipped": skipped_count,
        "root_accounts": list(set(root_accounts)) # Unique list
    }


def ensure_accounts_settings(organization):
    """
    Create Accounts Settings for the organization if missing.
    """
    if frappe.db.exists("Accounts Settings", organization):
        return

    defaults = {
        "default_receivable_account": get_account_by_name(organization, "Accounts Receivable"),
        "default_cash_account": get_account_by_name(organization, "Cash"),
        "default_bank_account": get_account_by_name(organization, "Bank"),
        "default_advance_account": get_account_by_name(organization, "Advances / Unearned Revenue"),
        "default_tax_payable_account": get_account_by_name(organization, "Tax Payable"),
    }

    missing = [key for key, value in defaults.items() if not value]
    if missing:
        frappe.throw(
            _("Missing default accounts for Accounts Settings: {0}").format(", ".join(missing))
        )

    settings = frappe.new_doc("Accounts Settings")
    settings.organization = organization
    settings.update(defaults)
    settings.insert(ignore_permissions=True)
