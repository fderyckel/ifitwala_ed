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

  refresh(frm) {
    if (frm.doc.follow_up_status === "Completed" && frappe.user.has_role("Academic Admin")) {
      frm.add_custom_button(__("Close Log"), function () {
        frm.set_value("follow_up_status", "Closed");
        frm.save();
      }, __("Actions"));
    }

    frm.add_custom_button(__("New Follow-Up"), () => {
      frappe.call({
        method: "ifitwala_ed.students.doctype.student_log.student_log.get_employee_data",
        callback(r) {
          frappe.new_doc("Student Log Follow Up", {
            student_log: frm.doc.name,
            //student: frm.doc.student,
            //student_name: frm.doc.student_name,
            author: r.message?.name || "",
            date: frappe.datetime.get_today()
          });
        }
      });
    });
  }, 

  student(frm) {
    if (!frm.doc.student) {
      frm.set_value("program", "");
      frm.set_value("academic_year", "");
      return;
    }
  
    frappe.call({
      method: "ifitwala_ed.students.doctype.student_log.student_log.get_active_program_enrollment",
      args: { student: frm.doc.student },
      callback: function (r) {
        if (r.message) {
          frm.set_value("program", r.message.program || "");
          frm.set_value("academic_year", r.message.academic_year || "");
        } else {
          frm.set_value("program", "");
          frm.set_value("academic_year", "");
          frappe.msgprint({
            message: __("No active Program Enrollment found for this student. Program and Academic Year were not set."),
            indicator: "orange",
            title: __("Missing Enrollment")
          });
        }
      }
    });
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
      args: { next_step: frm.doc.next_step },
      callback(r) {
        if (r.message) {
          frm.set_value("follow_up_role", r.message);
  
          const school = frm.doc.program
            ? frappe.model.get_value("Program", frm.doc.program, "school")
            : null;
  
          frm.set_query("follow_up_person", () => ({
            query: "ifitwala_ed.api.get_employees_with_role",
            filters: {
              role: r.message,
              school: school || ""
            }
          }));
        }
      }
    });
  }, 

  requires_follow_up(frm) {
    const show = frm.doc.requires_follow_up === 1;
    frm.toggle_display(['next_step', 'follow_up_role', 'follow_up_person', 'follow_up_status'], show);

    if (!show) {
      frm.set_value('follow_up_status', 'Closed');
    } else if (!frm.doc.follow_up_status || frm.doc.follow_up_status === 'Closed') {
      frm.set_value('follow_up_status', 'Open');
    }
  },

});

frappe.realtime.on("follow_up_started", function (data) {
  frappe.show_alert({
    message: __("Follow-up started for {0}", [data.student_name || data.log_name]),
    indicator: "orange"
  });
});