// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings['Program Enrollment'] = {
    onload: function(listview) {
        listview.page.fields_dict['academic_year'].get_query = function() {
            return { query: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.academic_year_link_query" };
        };
    }
};
