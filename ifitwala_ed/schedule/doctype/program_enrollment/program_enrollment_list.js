// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings["Program Enrollment"] = {
  hide_name_column: true,
	add_fields: ["student", "archived", "student_cohort", "program", "term"], 
  colwidths: {
    student: 4,
    archived: 1,
    student_cohort: 2,
    program: 2,
    term: 1,
  },
};
