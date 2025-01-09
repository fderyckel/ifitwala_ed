// Copyright (c) 2025, François de Ryckel 
// For license information, please see license.txt

frappe.listview_settings['Student'] = {
    hide_name_column: true, 
    add_fields: ["student_gender", "docstatus"], 
    get_indicator: function (doc) {
        if (doc.student_gender === "Female") { 
            return [__("Female"), "red", "student_gender,=,Female"]; // Light pink
        } else if (doc.student_gender === "Male") {
            return [__("Male"), "blue", "student_gender,=,Male"]; // Light blue
        } else {
            return [__("Other"), "green", "student_gender,=,Other"]; // Light brown (tan)
        }
    }
};