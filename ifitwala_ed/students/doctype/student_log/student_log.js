// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Log", {
  onload(frm) {
    // Only set defaults if creating a new doc
    if (frm.is_new()) {
      // If date is empty, set it to today's date
      if (!frm.doc.date) {
        frm.set_value("date", frappe.datetime.get_today());
      }
      // If time is empty, set it to current time
      if (!frm.doc.time) {
        frm.set_value("time", frappe.datetime.now_time());
      }
    }
  }, 

  refresh(frm) {
    // If creating a new doc and no author is set, fetch the current user’s Employee
    if (frm.is_new() && !frm.doc.author) {
      frappe.call({
        method: "ifitwala_ed.students.doctype.student_log.student_log.get_employee_data",
        callback: function(r) {
          if (r && r.message && r.message.name) {
            frm.set_value("author", r.message.name);
            frm.set_value("author_name", r.message.employee_full_name);
          }
        }
      });
    }
  }, 
  
  author(frm) {
    // Whenever 'author' changes, fetch corresponding full name
    if (frm.doc.author) {
      frappe.call({
        method: "ifitwala_ed.students.doctype.student_log.student_log.get_employee_data",
        args: {
          employee_name: frm.doc.author
        },
        callback: function(r) {
          if (r && r.message && r.message.name) {
            frm.set_value("author_name", r.message.employee_full_name);
          } else {
            frm.set_value("author_name", "");
          }
        }
      });
    } else {
      // If author is cleared, also clear author_name
      frm.set_value("author_name", "");
    }
  }  
});
