// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Course Enrollment Tool", { 
  onload: function(frm) { 
    // Hide term field by default
    frm.set_df_property("term", "hidden", 1);
    
    // Set academic_year filter based on selected program
    frm.set_query("academic_year", function () {
      return {
        query: "ifitwala_ed.schedule.doctype.course_enrollment_tool.course_enrollment_tool.get_academic_years_from_program",
        filters: {
          program: frm.doc.program
        }
      };
    });
  },

  program: function(frm) {
    frm.set_value("academic_year", null);
  }, 

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

  course: async function(frm) {
    if (!frm.doc.course) {
      frm.set_df_property("term", "hidden", 1);
      return;
    }
  
    // Fetch Course to check if it's term-long
    const course = await frappe.db.get_doc("Course", frm.doc.course);
    const is_term_long = !!course.term_long;
  
    // Show or hide 'term' field
    frm.set_df_property("term", "hidden", !is_term_long);
  
    if (!is_term_long) {
      frm.set_value("term", null);
    }
  },
  
  // 4) Single button "Add Course" that calls add_course_to_program_enrollment() on the server
  add_course: function(frm) {
    frappe.call({
      doc: frm.doc,
      method: "add_course_to_program_enrollment",
      callback: function(r) {
        if (!r.exc) {
          frm.reload_doc();
        }
      }
    });
  }
});


frappe.ui.form.on("Course Enrollment Tool Student", {
  student: function(frm, cdt, cdn) {
    const row = frappe.get_doc(cdt, cdn);

    // Only run if Program, Academic Year are set in the parent
    if (!frm.doc.program || !frm.doc.academic_year) {
      frappe.msgprint(__("Please select Program and Academic Year first"));
      return;
    }

    // Attempt to find an existing Program Enrollment for the Student, Program, Year, Term
    frappe.call({
      method: "frappe.client.get_value",
      args: {
        doctype: "Program Enrollment", 
        fieldname: "name", 
        filters: {
          student: row.student,
          program: frm.doc.program,
          academic_year: frm.doc.academic_year
        }
      },
      callback: function(r) {
        if (r.message && r.message.name) {
          // Found a matching Program Enrollment
          frappe.model.set_value(cdt, cdn, "program_enrollment", r.message.name);
        } else {
          // No Program Enrollment found => either leave it blank or handle differently
          frappe.model.set_value(cdt, cdn, "program_enrollment", null);
        }
      }
    });
  }
});
