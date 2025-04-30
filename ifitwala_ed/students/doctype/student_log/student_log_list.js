// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings['Student Log'] = {
  get_indicator(doc) {
    const sstatus = (doc.follow_up_status || "").trim().toLowerCase();

    if (sstatus === "closed") {
      return [__("Closed"), "green", "follow_up_status,=,Closed"];
    } else if (sstatus === "completed") {
      return [__("Completed"), "blue", "follow_up_status,=,Completed"];
    } else if (sstatus === "open") {
      return [__("Open"), "red", "follow_up_status,=,Open"];
    } else {
      return [__("In Progress"), "orange", "follow_up_status,=,In Progress"];
    }
  }, 
  
  // Remove "ID" (i.e., name) column
  hide_name_column: true
};
