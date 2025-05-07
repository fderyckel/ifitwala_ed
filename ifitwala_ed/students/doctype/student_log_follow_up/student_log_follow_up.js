// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Log Follow Up", {
  onload(frm) {
      // Set author_name if not already set
      if (!frm.doc.author_name) {
          frappe.call({
              method: "ifitwala_ed.students.doctype.student_log.student_log.get_employee_data",
              callback: function (r) {
                  if (r && r.message && r.message.employee_full_name) {
                      frm.set_value("author_name", r.message.employee_full_name);
                  }
              }
          });
      }
  },

  refresh(frm) {
      // Ensure author_name is always populated on refresh
      if (!frm.doc.author_name) {
          frappe.call({
              method: "ifitwala_ed.students.doctype.student_log.student_log.get_employee_data",
              callback: function (r) {
                  if (r && r.message && r.message.employee_full_name) {
                      frm.set_value("author_name", r.message.employee_full_name);
                  }
              }
          });
      }
  }
});
