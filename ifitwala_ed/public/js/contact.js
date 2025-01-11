// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Contact", {
	refresh(frm) {
		frm.set_query("link_doctype", "links", function () {
			return {
				query: "frappe.contacts.address_and_contact.filter_dynamic_link_doctypes",
				filters: {
					fieldtype: ["in", ["HTML", "Text Editor"]],
					fieldname: ["in", ["contact_html", "company_description"]],
				},
			};
		});
		frm.refresh_field("links");
	},
});