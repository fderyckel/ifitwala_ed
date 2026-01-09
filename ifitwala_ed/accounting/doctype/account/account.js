frappe.ui.form.on('Account', {
	setup: function(frm) {
		frm.set_query('parent_account', function(doc) {
			return {
				filters: {
					'is_group': 1,
					'organization': doc.organization,
                    'name': ['!=', doc.name]
				}
			};
		});
        
        frm.set_query('organization', function(doc) {
            // If parent is set, lock organization to parent's organization?
            // Usually we start with Org. 
            return {};
        });
	},
    
    refresh: function(frm) {
        // Read-only logic for Root accounts?
        if (!frm.is_new() && !frm.doc.parent_account) {
            frm.set_intro(__("This is a root account."));
        }
    }
});
