// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Program Enrollment", {
  onload: function (frm) {

    // to filter academic year by descending order  
    frm.set_query("academic_year", function () {
      return {
        query: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_academic_years",
        filters: {
          school: frm.doc.school
        },
      };
    });
  },

  onload_post_render: function (frm) {
    // Filter term_start in child table based on academic_year
    frm.set_query("term_start", "courses", function (doc, cdt, cdn) {
      return {
        filters: {
          academic_year: frm.doc.academic_year
        }
      };
    });

    // Filter term_end in child table based on academic_year
    frm.set_query("term_end", "courses", function (doc, cdt, cdn) {
      return {
        filters: {
          academic_year: frm.doc.academic_year
        }
      };
    });

    frm.get_field("courses").grid.set_multiple_add("course");
    
    frm.set_query("course", "courses", function (doc, cdt, cdn) {
      return {
        query: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_program_courses",
        filters: {
          program: frm.doc.program
        },
      };
    });
  },

  program: function (frm) {
    frm.set_value("academic_year", null);
    frm.set_value("courses", []);
    frm.events.get_courses(frm);

    // Once school is fetched (read-only), apply academic year filter
    if (frm.doc.school) {
      frm.set_query("academic_year", function () {
        return {
          query: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_academic_years",
          filters: {
            school: frm.doc.school
          }
        };
      });
    }    
  },

  academic_year: function (frm) {
    // Just set the student query based on academic_year
    frm.set_value("student", null);

    frm.set_query("student", function () {
      return {
        query: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_students",
        filters: {
          academic_year: frm.doc.academic_year
        },
      };
    });
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
