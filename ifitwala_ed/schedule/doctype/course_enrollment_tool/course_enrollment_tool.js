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
        // This is the path to your whitelisted Python method in course_enrollment_tool.py
        // e.g. "my_app.my_module.course_enrollment_tool.fetch_eligible_students"
        query: "ifitwala_ed.schedule.doctype.course_enrollment_tool.fetch_eligible_students",
        // We can pass filters to the Python method as needed.
        // The standard Link query expects a structure where the method can handle
        // doctype, txt, searchfield, page_len, start, filters, etc.
        // But for simplicity, you can check `filters` directly in your code.
        filters: {
          academic_year: frm.doc.academic_year,
          program: frm.doc.program,
          term: frm.doc.term,
          course: frm.doc.course
        }
      };
    });
  },

  // 3) Single button "Add Course" that calls add_course_to_program_enrollment() on the server
  add_course: function(frm) {
    frappe.call({
      doc: frm.doc,
      method: "ifitwala_ed.schedule.doctype.course_enrollment_tool.add_course_to_program_enrollment",
      callback: function(r) {
        if (!r.exc) {
          frm.reload_doc();
        }
      }
    });
  }
});

