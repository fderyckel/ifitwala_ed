// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Log Follow Up", {
  onload(frm) {
      // Set follow_up_author if not already set
      if (!frm.doc.follow_up_author) {
          frappe.call({
              method: "ifitwala_ed.students.doctype.student_log.student_log.get_employee_data",
              callback: function (r) {
                  if (r && r.message && r.message.employee_full_name) {
                      frm.set_value("follow_up_author", r.message.employee_full_name);
                  }
              }
          });
      }

    // Set current date if not already set
    if (!frm.doc.date) {
        frm.set_value("date", frappe.datetime.get_today());
    }
  },

  refresh(frm) {
      // Ensure follow_up_author is always populated on refresh
      if (!frm.doc.follow_up_author) {
          frappe.call({
              method: "ifitwala_ed.students.doctype.student_log.student_log.get_employee_data",
              callback: function (r) {
                  if (r && r.message && r.message.employee_full_name) {
                      frm.set_value("follow_up_author", r.message.employee_full_name);
                  }
              }
          });
      }

    // Ensure date is always set on refresh
    if (!frm.doc.date) {
        frm.set_value("date", frappe.datetime.get_today());
    }
  }
});
