// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// searches for enabled users
frappe.provide("ifitwala_ed.queries");

$.extend(ifitwala_ed.queries, {
	user: function () {
		return { query: "frappe.core.doctype.user.user.user_query" };
	},

	//task: function () {
	//	return { query: "erpnext.projects.utils.query_task" };
	//},

	contact_query: function (doc) {
		if (frappe.dynamic_link) {
			if (!doc[frappe.dynamic_link.fieldname]) {
				cur_frm.scroll_to_field(frappe.dynamic_link.fieldname);
				frappe.show_alert({
					message: __("Please set {0} first.", [
						__(frappe.meta.get_label(doc.doctype, frappe.dynamic_link.fieldname, doc.name)),
					]),
					indicator: "orange",
				});
			}

			return {
				query: "frappe.contacts.doctype.contact.contact.contact_query",
				filters: {
					link_doctype: frappe.dynamic_link.doctype,
					link_name: doc[frappe.dynamic_link.fieldname],
				},
			};
		}
	},

	company_contact_query: function (doc) {
		if (!doc.company) {
			frappe.throw(__("Please set {0}", [__(frappe.meta.get_label(doc.doctype, "company", doc.name))]));
		}

		return {
			query: "frappe.contacts.doctype.contact.contact.contact_query",
			filters: { link_doctype: "Company", link_name: doc.company },
		};
	},

	address_query: function (doc) {
		if (frappe.dynamic_link) {
			if (!doc[frappe.dynamic_link.fieldname]) {
				cur_frm.scroll_to_field(frappe.dynamic_link.fieldname);
				frappe.show_alert({
					message: __("Please set {0} first.", [
						__(frappe.meta.get_label(doc.doctype, frappe.dynamic_link.fieldname, doc.name)),
					]),
					indicator: "orange",
				});
			}

			return {
				query: "frappe.contacts.doctype.address.address.address_query",
				filters: {
					link_doctype: frappe.dynamic_link.doctype,
					link_name: doc[frappe.dynamic_link.fieldname],
				},
			};
		}
	},

	company_address_query: function (doc) {
		if (!doc.company) {
			cur_frm.scroll_to_field("company");
			frappe.show_alert({
				message: __("Please set {0} first.", [
					__(frappe.meta.get_label(doc.doctype, "company", doc.name)),
				]),
				indicator: "orange",
			});
		}

		return {
			query: "frappe.contacts.doctype.address.address.address_query",
			filters: { link_doctype: "Company", link_name: doc.company },
		};
	},

	not_a_group_filter: function () {
		return { filters: { is_group: 0 } };
	},

	employee: function () {
		return { query: "ifitwala_ed.controllers.queries.employee_query" };
	},

	location: function (doc) {
		return {
			filters: [
				["Location", "organization", "in", ["", cstr(doc.organization)]],
				["Location", "is_group", "=", 0],
			],
		};
	},
});

erpnext.queries.setup_queries = function (frm, options, query_fn) {
	var me = this;
	var set_query = function (doctype, parentfield) {
		var link_fields = frappe.meta.get_docfields(doctype, frm.doc.name, {
			fieldtype: "Link",
			options: options,
		});
		$.each(link_fields, function (i, df) {
			if (parentfield) {
				frm.set_query(df.fieldname, parentfield, query_fn);
			} else {
				frm.set_query(df.fieldname, query_fn);
			}
		});
	};

	set_query(frm.doc.doctype);

	// warehouse field in tables
	$.each(
		frappe.meta.get_docfields(frm.doc.doctype, frm.doc.name, { fieldtype: "Table" }),
		function (i, df) {
			set_query(df.options, df.fieldname);
		}
	);
};

