// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings['Student Log'] = {
  add_fields: ["follow_up_status", "docstatus"],
	get_indicator(doc) {
		const sstatus = (doc.follow_up_status || "").trim().toLowerCase();

		// Draft (or Open while still draft) → red
		if (doc.docstatus === 0 && (!sstatus || sstatus === "open")) {
			return [__("Draft"), "red", "docstatus,=,0"];
		}

		// Completed → blue
		if (sstatus === "completed") {
			return [__("Completed"), "green", "follow_up_status,=,Completed"];
		}

		// Open → red
		if (sstatus === "open") {
			return [__("Open"), "red", "follow_up_status,=,Open"];
		}

		// Default: In Progress → orange
		return [__("In Progress"), "orange", "follow_up_status,=,In Progress"];
	},
};
