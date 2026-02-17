// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Course Group", {
  refresh(frm) {
    if (!frm.is_new()) {
      frm.add_custom_button(__("Add Courses"), () => {
        frappe.new_doc("Course", {}, course => {
          course.course_group = frm.doc.name;
        });
      });
    }
 	},
});
