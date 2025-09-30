// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/students/doctype/guardian/guardian.js

frappe.ui.form.on("Guardian", {
	refresh(frm) {
		frappe.dynamic_link = { doc: frm.doc, fieldname: "name", doctype: "Guardian" };
		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);
		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}

		if (!frm.doc.user && !frm.is_new()) {
			frm.add_custom_button(__("Create and Invite as User"), () => {
				frappe.call({
					method: "ifitwala_ed.students.doctype.guardian.guardian.invite_guardian",
					args: { guardian: frm.doc.name }
				}).then(() => {
					frm.reload_doc(); // pulls the server-updated "user" value without saving the form
				});
			});
		}
	},

	salutation(frm) {
		if (!frm.doc.salutation) return;
		const map = {
			"Mr": "Male",
			"Ms": "Female",
			"Mrs": "Female",
			"Miss": "Female",
			"Mx": "Prefer Not To Say",
		};
		const v = map[frm.doc.salutation];
		if (v) frm.set_value("guardian_gender", v);
	},
});
