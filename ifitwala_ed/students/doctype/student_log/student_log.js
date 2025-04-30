// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Log", {
  onload(frm) {
    frm.set_query("student", () => {
      return {
        filters: {
          enabled: 1
        }
      };
    });

    if (frm.is_new()) {
      // Set default date and time if not already set
      if (!frm.doc.date) {
        frm.set_value("date", frappe.datetime.get_today());
      }
      if (!frm.doc.time) {
        frm.set_value("time", frappe.datetime.now_time());
      }

      // Set author if not yet set
      if (!frm.doc.author) {
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
    } 
  },

  student(frm) {
    if (frm.doc.student) {
      frappe.call({
        method: "ifitwala_ed.students.doctype.student_log.student_log.get_active_program_enrollment",
        args: {
          student: frm.doc.student
        },
        callback: function(r) {
          if (r.message) {
            frm.set_value("program", r.message.program || "");
            frm.set_value("academic_year", r.message.academic_year || "");
          } else {
            frm.set_value("program", "");
            frm.set_value("academic_year", "");
            frappe.show_alert({
              message: __("No active Program Enrollment found for this student."), 
              indicator: "orange"
            });
          }
        }
      });
    } else {
      frm.set_value("program", "");
      frm.set_value("academic_year", "");
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
  }, 
  
  next_step(frm) {
    if (!frm.doc.next_step) return;
  
    frappe.call({
      method: "ifitwala_ed.students.doctype.student_log.student_log.get_follow_up_role_from_next_step",
      args: {
        next_step: frm.doc.next_step
      },
      callback(r) {
        if (r.message) {
          frm.set_value("follow_up_role", r.message);
  
          frm.set_query("follow_up_person", () => {
            return {
              query: "ifitwala_ed.api.get_employees_with_role",
              filters: {
                role: r.message,
                school: frm.doc.school || frm.doc.program && get_school_from_program(frm.doc.program)
              }
            };
          });
        }
      }
    });
  },

});
