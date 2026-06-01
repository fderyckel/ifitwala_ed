function get_account_tree_settings() {
	return frappe.treeview_settings["Account"];
}

function set_account_tree_scope(context) {
	const settings = get_account_tree_settings();
	settings._allowed_organizations = context.allowed_organizations || [];
	settings._unrestricted = !!context.unrestricted;
}

function get_account_organization_query() {
	const settings = get_account_tree_settings();
	if (settings._unrestricted) {
		return {};
	}

	const allowed_organizations = settings._allowed_organizations || [];
	if (!allowed_organizations.length) {
		return { filters: [["Organization", "name", "=", "___NONE___"]] };
	}

	return { filters: [["Organization", "name", "in", allowed_organizations]] };
}

function show_account_tree_scope_message(treeview, message) {
	if (!message) {
		return;
	}

	if (treeview.page && treeview.page.set_indicator) {
		treeview.page.set_indicator(__("No Organization scope"), "orange");
	}
	frappe.show_alert({ message, indicator: "orange" });
}

function make_account_tree(treeview, context) {
	const organization = context.default_organization || "";
	const field = treeview.page && treeview.page.fields_dict && treeview.page.fields_dict.organization;

	if (organization && field && field.set_value) {
		Promise.resolve(field.set_value(organization)).then(() => treeview.make_tree());
		return;
	}

	show_account_tree_scope_message(treeview, context.message);
	treeview.make_tree();
}

frappe.treeview_settings["Account"] = {
	title: __("Chart of Accounts"),
	breadcrumb: __("Accounting"),
	root_label: __("Chart of Accounts"),
	get_tree_root: false,
	get_tree_nodes: "ifitwala_ed.accounting.doctype.account.account.get_children",
	add_tree_node: "frappe.desk.treeview.add_node",
	show_expand_all: true,
	ignore_fields: ["parent_account"],
	filters: [
		{
			fieldname: "organization",
			fieldtype: "Link",
			label: __("Organization"),
			options: "Organization",
			reqd: 1,
			get_query: get_account_organization_query,
		},
	],
	fields: [
		{ fieldtype: "Data", fieldname: "account_name", label: __("Account Name"), reqd: 1 },
		{ fieldtype: "Data", fieldname: "account_number", label: __("Account Number") },
		{ fieldtype: "Check", fieldname: "is_group", label: __("Is Group") },
		{
			fieldtype: "Select",
			fieldname: "root_type",
			label: __("Root Type"),
			options: ["Asset", "Liability", "Equity", "Income", "Expense"].join("\n"),
			depends_on: "eval:doc.is_group && !doc.parent_account",
		},
		{
			fieldtype: "Select",
			fieldname: "account_type",
			label: __("Account Type"),
			options: frappe.get_meta("Account").fields.find((field) => field.fieldname === "account_type")?.options || "",
		},
		{
			fieldtype: "Link",
			fieldname: "account_currency",
			label: __("Currency"),
			options: "Currency",
		},
	],
	onload(treeview) {
		const settings = get_account_tree_settings();
		settings._tree = treeview;
		settings._allowed_organizations = [];
		settings._unrestricted = false;

		frappe.call({
			method: "ifitwala_ed.accounting.doctype.account.account.get_account_tree_context",
			callback(r) {
				const context = (r && r.message) || {};
				set_account_tree_scope(context);
				make_account_tree(treeview, context);
			},
			error() {
				show_account_tree_scope_message(
					treeview,
					__("Unable to resolve your Organization scope for the Chart of Accounts.")
				);
				treeview.make_tree();
			},
		});
	},
};
