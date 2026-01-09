frappe.ui.form.on('Account Holder', {
	refresh: function(frm) {
        if (!frm.is_new()) {
            frm.add_custom_button(__('View Students'), function() {
                frappe.route_options = {
                    'account_holder': frm.doc.name
                };
                frappe.set_route('List', 'Student');
            });
        }
	}
});
