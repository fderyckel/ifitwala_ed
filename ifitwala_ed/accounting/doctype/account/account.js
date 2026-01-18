frappe.ui.form.on("Account", {
	setup: function (frm) {
		frm.add_fetch("parent_account", "report_type", "report_type");
		frm.add_fetch("parent_account", "root_type", "root_type");
	},
	onload: function (frm) {
		frm.set_query("parent_account", function (doc) {
			return {
				filters: {
					is_group: 1,
					organization: doc.organization,
				},
			};
		});
	},
});
