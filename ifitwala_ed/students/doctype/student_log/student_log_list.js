// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings['Student Log'] = {
  get_indicator(doc) {
    const status = (doc.follow_up_status || "").trim().toLowerCase();

    if (status === "closed") {
      return [__("Closed"), "green", "follow_up_status,=,Closed"];
    } else if (status === "completed") {
      return [__("Completed"), "blue", "follow_up_status,=,Completed"];
    } else if (status === "open") {
      return [__("Open"), "red", "follow_up_status,=,Open"];
    } else {
      return [__("In Progress"), "orange", "follow_up_status,=,In Progress"];
    }
  }
};
