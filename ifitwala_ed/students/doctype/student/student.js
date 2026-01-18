frappe.ui.form.on('Student', {
	refresh: function(frm) {
        if (!frm.doc.__islocal) {
            frm.trigger('setup_account_holder_filter');
        }
	},
    
    anchor_school: function(frm) {
        frm.trigger('setup_account_holder_filter');
    },
    
    setup_account_holder_filter: function(frm) {
        if (frm.doc.anchor_school) {
             frappe.call({
                method: "ifitwala_ed.accounting.account_holder_utils.get_school_organization",
                args: { school: frm.doc.anchor_school },
                callback: function(r) {
                    if (r.message) {
                        frm.set_query("account_holder", function() {
                            return {
                                filters: {
                                    organization: r.message
                                }
                            };
                        });
                    }
                }
             });
        }
    }
});
