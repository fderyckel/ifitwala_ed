frappe.listview_settings["Sales Invoice"] = {
	add_fields: [
		"account_holder",
		"grand_total",
		"outstanding_amount",
		"posting_date",
		"organization",
	],
	get_indicator: function (doc) {
		if (doc.docstatus === 0) {
			return [__("Draft"), "red", "docstatus,=,0"];
		}
		if (doc.docstatus === 2) {
			return [__("Cancelled"), "grey", "docstatus,=,2"];
		}
		if (doc.outstanding_amount === 0) {
			return [__("Paid"), "green", "outstanding_amount,=,0"];
		}
		return [__("Unpaid"), "orange", "outstanding_amount,>,0"];
	},
	right_column: "grand_total",
};
