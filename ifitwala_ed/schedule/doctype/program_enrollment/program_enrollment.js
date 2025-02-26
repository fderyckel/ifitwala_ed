// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Program Enrollment", {
  onload: function (frm) {
    // to filter academic terms that matches the given academic year.
    frm.set_query("term", function () {
      return {
        filters: {
          academic_year: frm.doc.academic_year,
        },
      };
    });

    // To filter the students showing up in the student fields (will not show up students already enrolled for that year  or term)
    // only  work if academic term or academic year have already been selected
    frm.set_query("student", function () {
      return {
        query:
          "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_students",
        filters: {
          academic_year: frm.doc.academic_year,
          term: frm.doc.term,
        },
      };
    });
  },

  onload_post_render: function (frm) {
    frm.get_field("courses").grid.set_multiple_add("course");
    
    frm.set_query("course", "courses", function (doc, cdt, cdn) {
      return {
        query: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_program_courses",
        filters: {program: frm.doc.program},
      };
    });
  },

  program: function (frm) {
    frm.events.get_courses(frm);
  },

  // to get the mandatory courses of a given program
  get_courses: function (frm) {
    frm.set_value("courses", []);
    frappe.call({
      method: "get_courses",
      doc: frm.doc,
      callback: function (r) {
        if (r.message) {
          frm.set_value("courses", r.message);
        }
      },
    });
  },
});
