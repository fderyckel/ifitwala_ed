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

      // Set author_name if not yet set
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
  },

  refresh(frm) {
    const is_author = frappe.session.user_fullname === frm.doc.author_name;
    const status = (frm.doc.follow_up_status || "").toLowerCase();

    // Show "New Follow-Up" button only if status is not "Completed"
    if (status !== "completed") {
        frm.add_custom_button(__("New Follow-Up"), () => {
            frappe.call({
                method: "ifitwala_ed.students.doctype.student_log.student_log.get_employee_data",
                callback(r) {
                    frappe.new_doc("Student Log Follow Up", {
                        student_log: frm.doc.name,
                        follow_up_author: r.message?.employee_full_name || "",
                        date: frappe.datetime.get_today()
                    });
                }
            });
        });
    }

    if (status === "closed" && is_author) {
      frm.add_custom_button(__("Mark as Completed"), function () {
        frm.call({
          method: "frappe.client.set_value",
          args: {
            doctype: "Student Log",
            name: frm.doc.name,
            fieldname: "follow_up_status",
            value: "Completed"
          },
          callback: function() {
            frappe.show_alert({
              message: __("Marked as Completed"),
              indicator: "green"
            });
            frm.reload_doc();  // Update the form to reflect the new status
          }
        });
      }, __("Actions"));
    }

    if (frm.doc.follow_up_status === "Completed" && frappe.user.has_role("Academic Admin")) {
      frm.add_custom_button(__("Finalize: Close Log"), function () {
        frappe.call({
          method: "frappe.client.set_value",
          args: {
            doctype: "Student Log",
            name: frm.doc.name,
            fieldname: "follow_up_status",
            value: "Closed"
          },
          callback: function() {
            frappe.show_alert({
              message: __("Log finalized and closed"),
              indicator: "red"
            });
            frm.reload_doc();  // Ensure UI is consistent
          }
        });
      }, __("Actions"));
    }
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
        if (r && r.message) {
          frm.set_value("program", r.message.program || "");
          frm.set_value("academic_year", r.message.academic_year || "");
        } else {
          console.warn("No active enrollment returned", r);
          frappe.msgprint({
            message: __("No active Program Enrollment found for this student."),
            indicator: "orange"
          });
        }
      },
      error: function(err) {
        console.error("Error in get_active_program_enrollment", err);
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
        const role = r.message || "Academic Staff";  // fallback role
        frm.set_value("follow_up_role", role);        // show in UI
  
        frm.set_query("follow_up_person", () => ({
          query: "ifitwala_ed.api.get_users_with_role",
          filters: {
            role: frm.doc.follow_up_role || "Academic Staff"
          }
        }));
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

frappe.realtime.on("follow_up_ready_to_review", function (data) {
  frappe.show_alert({
    message: __("A follow-up for {0} is now ready for your review.", [data.student_name || data.log_name]),
    indicator: "green"
  });
});
