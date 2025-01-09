// Copyright (c) 2025, François de Ryckel 
// For license information, please see license.txt

frappe.listview_settings['Student'] = {
    hide_name_column: true, // Keep this if you want to hide the name column

    get_indicator: function(doc) {

        const gender_colors = {
            "Female": "pink",
            "Male": "light-blue",
            "Other": "green"
        };

        let indicator_color = gender_colors[doc.student_gender] || "gray"; // Default to gray if not found

        return [__(doc.student_gender), indicator_color,'student_gender,=,${doc.student_gender}'];
    }
};