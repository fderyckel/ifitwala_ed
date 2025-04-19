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
    // Filter term fields in child table
    ["term_start", "term_end"].forEach((field) => {
      frm.set_query(field, "courses", function () {
        const filters = {};
        if (frm.doc.academic_year) filters.academic_year = frm.doc.academic_year;
        if (frm.doc.school) filters.school = frm.doc.school;
        return { filters };
      });
    });
  
    frm.get_field("courses").grid.set_multiple_add("course");
  
    // Initial course filter setup — if program is already set on load
    if (frm.doc.program) {
      frappe.call({
        method: "frappe.db.get_list",
        args: {
          doctype: "Program Course",
          fields: ["course"],
          filters: { parent: frm.doc.program },
          limit_page_length: 1000
        },
        callback: function (r) {
          const valid_courses = (r.message || []).map(row => row.course);
          frm.valid_program_courses = valid_courses;
  
          frm.fields_dict["courses"].grid.get_field("course").get_query = function (doc) {
            const selected_courses = (doc.courses || []).map(row => row.course).filter(Boolean);
            return {
              filters: [
                ["Course", "name", "in", valid_courses.filter(c => !selected_courses.includes(c))]
              ]
            };
          };
        }
      });
    }
  }, 

  program: function (frm) {
    frm.set_value("academic_year", null);
    frm.set_value("courses", []);
    frm.term_bounds_cache = {};
  
    frm.events.get_courses(frm);
  
    // Set academic year filter
    if (frm.doc.school) {
      frm.set_query("academic_year", function () {
        return {
          query: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_academic_years",
          filters: { school: frm.doc.school }
        };
      });
    }
  
    // Refresh course query for this program
    frappe.call({
      method: "frappe.db.get_list",
      args: {
        doctype: "Program Course",
        fields: ["course"],
        filters: { parent: frm.doc.program },
        limit_page_length: 1000
      },
      callback: function (r) {
        const valid_courses = (r.message || []).map(row => row.course);
        frm.valid_program_courses = valid_courses;
  
        frm.fields_dict["courses"].grid.get_field("course").get_query = function (doc) {
          const selected_courses = (doc.courses || []).map(row => row.course).filter(Boolean);
          return {
            filters: [
              ["Course", "name", "in", valid_courses.filter(c => !selected_courses.includes(c))]
            ]
          };
        };
      }
    });
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

frappe.ui.form.on("Program Enrollment Course", {
  course: async function (frm, cdt, cdn) {
    const row = frappe.get_doc(cdt, cdn);

    // 1. Set default status if not set
    if (!row.status) {
      frappe.model.set_value(cdt, cdn, "status", "Enrolled");
    }

    // 2. Get Course doc to check if it's year-long
    if (row.course && frm.doc.school) {
      const course = await frappe.db.get_doc("Course", row.course);

      if (!course.term_long) {
        // Init cache container if not already done
        frm.term_bounds_cache = frm.term_bounds_cache || {};

        // Use cached term bounds if available
        if (!frm.term_bounds_cache[frm.doc.school]) {
          const res = await frappe.call({
            method: "ifitwala_ed.schedule.schedule_utils.get_school_term_bounds",
            args: { 
              school: frm.doc.school, 
              academic_year: frm.doc.academic_year
            }
          });

          frm.term_bounds_cache[frm.doc.school] = res.message || {};
        }

        const bounds = frm.term_bounds_cache[frm.doc.school];
        if (bounds.term_start) {
          frappe.model.set_value(cdt, cdn, "term_start", bounds.term_start);
        }
        if (bounds.term_end) {
          frappe.model.set_value(cdt, cdn, "term_end", bounds.term_end);
        }
      }
    }
  }
});
