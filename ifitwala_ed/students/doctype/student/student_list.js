// Copyright (c) 2025, François de Ryckel 
// For license information, please see license.txt

frappe.listview_settings['Student'] = {
    hide_name_column: true, 
    add_fields: ["student_gender"], 
    get_indicator: function (doc) {
        if (doc.student_gender === "Female") {
            console.log("Applying female-indicator to", doc.name); // Debugging log
            return [__("Female"), "female-indicator", "student_gender,=,Female"]; // Light pink
        } else if (doc.student_gender === "Male") {
            console.log("Applying male-indicator to", doc.name); // Debugging log
            return [__("Male"), "male-indicator", "student_gender,=,Male"]; // Light blue
        } else {
            return [__("Other"), "other-indicator", "student_gender,=,Other"]; // Light brown (tan)
        }
    }
};