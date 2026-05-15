frappe.listview_settings["Sales Invoice"] = {
	add_fields: [
		"account_holder",
		"grand_total",
		"outstanding_amount",
		"posting_date",
		"organization",
		"status",
		"adjustment_type",
	],
	get_indicator(doc) {
		const palette = {
			Draft: "red",
			Cancelled: "grey",
			Unpaid: "orange",
			"Partly Paid": "yellow",
			Paid: "green",
			Overdue: "red",
			"Credit Note": "blue",
			"Partly Credited": "cyan",
			Credited: "blue",
		};
		const status = doc.status || (doc.docstatus === 2 ? "Cancelled" : "Draft");
		return [status, palette[status] || "orange", `status,=,${status}`];
	},
	right_column: "grand_total",
};
