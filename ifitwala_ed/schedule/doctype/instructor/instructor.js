// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/schedule/doctype/instructor/instructor.js

frappe.ui.form.on("Instructor", {
	onload(frm) {
		// restrict employee list to allowed schools
		frappe.call({
			method: "ifitwala_ed.utilities.school_tree.get_descendant_schools",
			args: { user_school: frappe.defaults.get_user_default("school") },
			callback: function (r) {
				let allowed = r.message || [];
				frm.set_query("employee", () => ({
					filters: { school: ["in", allowed] }
				}));
			}
		});
	},

});
