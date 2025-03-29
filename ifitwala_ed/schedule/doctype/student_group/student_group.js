// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Group", {
  onload: function (frm) {
    frm.add_fetch("student", "student_full_name", "student_name");
    // will filter the academic terms  based on the chosen academic year.
    frm.set_query("term", function () {
      return {
        filters: {
          academic_year: frm.doc.academic_year,
        },
      };
    });

    if (!frm.__islocal) {
      frm.set_query("student", "students", function () {
        return {
          query:
            "ifitwala_ed.schedule.doctype.student_group.student_group.fetch_students",
          filters: {
            academic_year: frm.doc.academic_year,
            group_based_on: frm.doc.group_based_on,
            term: frm.doc.term,
            program: frm.doc.program,
            cohort: frm.doc.cohort,
            course: frm.doc.course,
            student_group: frm.doc.name,
          },
        };
      });
    }
  },

  refresh: function (frm) {
    if (!frm.doc.__islocal) {
      frm.add_custom_button(__('Open Student Cards'), () => {
        frappe.route_options = { student_group: frm.doc.name };
        frappe.set_route('student_group_cards');
      });
    }  

    if (!frm.doc.__islocal && !in_list(frappe.user_roles, "Student")) {
      frm.add_custom_button(
        __("Add a session"),
        function () {
          frappe.route_options = {
            event_category: "Course",
            event_type: "Private",
            reference_type: "Student Group",
            reference_name: frm.doc.name,
          };
          frappe.set_route("List", "School Event");
        },
      );
    }
  },

  program: function (frm) {
    if (frm.doc.program) {
      frm.set_query("course", function () {
        return {
          query:
            "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_program_courses",
          filters: {
            program: frm.doc.program,
          },
        };
      });
    }
  },

  group_based_on: function (frm) {
    if (frm.doc.group_based_on == "Cohort") {
      frm.doc.course = null;
      frm.set_df_property("program", "reqd", 0);
      frm.set_df_property("course", "reqd", 0);
      frm.set_df_property("cohort", "reqd", 1);
    } else if (frm.doc.group_based_on == "Course") {
      //frm.set_df_property("program", "reqd", 1);
      frm.set_df_property("course", "reqd", 1);
    } else if (frm.doc.group_based_on == "Activity") {
      frm.set_df_property("program", "reqd", 0);
      frm.set_df_property("course", "reqd", 0);
    }
  },

  get_students: function (frm) {
    if (
      frm.doc.group_based_on == "Cohort" ||
      frm.doc.group_based_on == "Course"
    ) {
      var student_list = [];
      var max_roll_no = 0;
      $.each(frm.doc.students, function (i, d) {
        student_list.push(d.student);
        if (d.group_roll_number > max_roll_no) {
          max_roll_no = d.group_roll_number;
        }
      });

      if (frm.doc.academic_year) {
        frappe.call({
          method:
            "ifitwala_ed.schedule.doctype.student_group.student_group.get_students",
          args: {
            academic_year: frm.doc.academic_year,
            term: frm.doc.term,
            group_based_on: frm.doc.group_based_on,
            program: frm.doc.program,
            cohort: frm.doc.cohort,
            course: frm.doc.course,
          },
          callback: function (r) {
            if (r.message) {
              $.each(r.message, function (i, d) {
                if (!in_list(student_list, d.student)) {
                  var s = frm.add_child("students");
                  s.student = d.student;
                  s.student_name = d.student_name;
                  if (d.active === 0) {
                    s.active = 0;
                  }
                  s.group_roll_number = ++max_roll_no;
                }
              });
              refresh_field("students");
              frm.save();
            } else {
              frappe.msgprint(__("Student Group is already updated."));
            }
          },
        });
      }
    } else {
      frappe.msgprint(
        __("Select students manually for the Activity based Group")
      );
    }
  },
});

frappe.ui.form.on("Student Group Instructor", {
  instructors_add: function (frm) {
    frm.fields_dict["instructors"].grid.get_field("instructor").get_query =
      function (doc) {
        let instructor_list = [];
        $.each(doc.instructors, function (idx, val) {
          instructor_list.push(val.instructor);
        });
        return { filters: [["Instructor", "name", "not in", instructor_list]] };
      };
  },
});
