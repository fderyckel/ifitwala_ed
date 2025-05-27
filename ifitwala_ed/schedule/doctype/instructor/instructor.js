// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt


frappe.ui.form.on("Instructor", {
	onload: function (frm) {
		frappe.call({
			method: "ifitwala_ed.utilities.school_tree.get_descendant_schools",
			args: {
				user_school: frappe.defaults.get_user_default("school")
			},
			callback: function (r) {
				let allowed_schools = r.message || [];

				frm.set_query("employee", function () {
					return {
						filters: {
							school: ["in", allowed_schools]
						}
					};
				});
			}
		});
	}
});
