// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Program Enrollment", {
  onload: function (frm) {

    // to filter academic year by descending order  
    frm.set_query("academic_year", function () {
      return {
        query: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_academic_years",
				filters: { school: frm.doc.school || null },
			};
    });

		// to filter the program from that school  
		frm.set_query("program", function () {
			return {
				filters: {
					school: frm.doc.school || null
				}
			};
		});
  },

  onload_post_render: function (frm) {
    // Filter term fields in child table
    ["term_start", "term_end"].forEach((field) => {
			frm.set_query(field, "courses", async function () {
				let allowed_schools = [];
				if (frm.doc.school) {
					const res = await frappe.call({
						method: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_allowed_term_schools",
						args: { school: frm.doc.school }
					});
					allowed_schools = res.message || [];
				}
				const filters = {};
				if (frm.doc.academic_year) filters.academic_year = frm.doc.academic_year;
				if (allowed_schools.length) filters.school = ["in", allowed_schools];
				return { filters };
			});
		});
  
    frm.get_field("courses").grid.set_multiple_add("course");
  
    // Initial course filter setup — if program is already set on load
    if (frm.doc.program) {
      frappe.call({
        method: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_program_courses_for_enrollment",
        args: {
          program: frm.doc.program
        },
        callback: function (r) {
          const valid_courses = r.message || [];
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
					filters: { school: frm.doc.school || null },
        };
      });
    }
  
    // Refresh course query for this program
    frappe.call({
      method: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_program_courses_for_enrollment",
      args: {
        program: frm.doc.program
      },
      callback: function (r) {
        const valid_courses = r.message || [];
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
    if (row.course && frm.doc.school && frm.doc.academic_year) {
      const course = await frappe.db.get_doc("Course", row.course);

      // Only proceed if this is not a term-based course
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
        if (bounds.term_start && bounds.term_end) {
          frappe.model.set_value(cdt, cdn, "term_start", bounds.term_start);
          frappe.model.set_value(cdt, cdn, "term_end", bounds.term_end);
        } else {
          // Fallback to first and last term if bounds are missing
          const terms = await frappe.db.get_list("Term", {
            filters: {
              school: frm.doc.school,
              academic_year: frm.doc.academic_year
            },
            fields: ["name", "term_start_date", "term_end_date"],
            order_by: "term_start_date asc"
          });

          if (terms.length > 0) {
            frappe.model.set_value(cdt, cdn, "term_start", terms[0].name);
            frappe.model.set_value(cdt, cdn, "term_end", terms[terms.length - 1].name);
          }
        }
      }
    }
  }
});

