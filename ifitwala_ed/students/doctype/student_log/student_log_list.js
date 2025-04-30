// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt
w
frappe.listview_settings['Student Log'] = {
  get_indicator(doc) {
    if (doc.follow_up_status === "Closed") {
      return [__("Closed"), "green", "follow_up_status,=,Closed"];
    } else if (doc.follow_up_status === "Completed") {
      return [__("Completed"), "blue", "follow_up_status,=,Completed"];
    } else if (doc.follow_up_status === "Open") {
      return [__("Open"), "red", "follow_up_status,=,Open"];
    } else {
      return [__("In Progress"), "orange", "follow_up_status,=,In Progress"];
    }
  }
};
