// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Course Enrollment Tool", {
  onload_post_render: function(frm) {
    // 1) Enable multiple add on the child table "students", for link field "student"
    frm.get_field("students").grid.set_multiple_add("student");

    // 2) Set a custom query so that when the user tries to pick a "Student" in the child table,
    //    Frappe calls our Python method "fetch_eligible_students" to filter the results.
    frm.set_query("student", "students", function(doc, cdt, cdn) {
      return {
        query: "ifitwala_ed.schedule.doctype.course_enrollment_tool.course_enrollment_tool.fetch_eligible_students",
        filters: {
          academic_year: frm.doc.academic_year,
          program: frm.doc.program,
          term: frm.doc.term,
          course: frm.doc.course
        }
      };
    });

    // 3) Set a custom query on the "course" field so that once Program is chosen,
    //    only courses from that Program appear in the dropdown.
    frm.set_query("course", function() {
      // If Program is not chosen, you can either return all courses or show an empty list.
      if (!frm.doc.program) {
        // Return an empty filter (aka show all courses)
        return {};
      }
      // Otherwise, call a custom server-side query that filters by Program
      return {
        query: "ifitwala_ed.schedule.doctype.course_enrollment_tool.course_enrollment_tool.get_courses_for_program",
        filters: {
          program: frm.doc.program
        }
      };
    }); 
  },

  // 4) Single button "Add Course" that calls add_course_to_program_enrollment() on the server
  add_course: function(frm) {
    frappe.call({
      doc: frm.doc,
      method: "ifitwala_ed.schedule.doctype.course_enrollment_tool.course_enrollment_tool.add_course_to_program_enrollment",
      callback: function(r) {
        if (!r.exc) {
          frm.reload_doc();
        }
      }
    });
  }
});

