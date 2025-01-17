// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Course", {
  setup: function (frm) {
    frm.add_fetch("team", "school", "school");
  },

  onload: function (frm) {}, 

  refresh: function (frm) {
    if (!cur_frm.doc.__islocal) {
      frm.add_custom_button(
        __("Add to Programs"),
        function () {
          frm.trigger("add_course_to_programs");
        }
      );
    }

    // to only suggest grade scale that are submitted (not cancel nor draft)
    frm.set_query("default_grade_scale", function () {
      return {
        filters: {
          docstatus: 1,
        },
      };
    });
  },

  add_course_to_programs: function (frm) {
    get_programs_without_course(frm.doc.name).then((r) => {
        if (r.message.length) {
            frappe.prompt(
                [
                    {
                        fieldname: "programs",
                        label: __("Programs"),
                        fieldtype: "MultiSelectPills",
                        get_data: function (txt) {
                            return r.message; // Use the program names directly
                        }
                    },
                    {
                        fieldtype: "Check",
                        label: __("Is Mandatory"),
                        fieldname: "mandatory",
                    },
                ],
                function (data) {
                    // --- Client-Side Modification Starts Here ---
                    if (data.programs && data.programs.length > 0) {
                        let update_promises = data.programs.map(program_name => {
                            return new Promise((resolve) => {
                                frappe.model.with_doc("Program", program_name, function () {
                                    let program_doc = frappe.get_doc("Program", program_name);
                                    let course_row = null;

                                    // Find the course in the program's child table
                                    for (let i = 0; i < program_doc.courses.length; i++) {
                                        if (program_doc.courses[i].course === frm.doc.name) {
                                            course_row = program_doc.courses[i];
                                            break;
                                        }
                                    }

                                    // If the course exists, update it, otherwise add it
                                    if (course_row) {
                                        course_row.mandatory = data.mandatory;
                                    } else {
                                        program_doc.append("courses", {
                                            course: frm.doc.name,
                                            course_name: frm.doc.course_name,
                                            mandatory: data.mandatory
                                        });
                                    }

                                    // Notify that the program doc has been updated
                                    program_doc.notify_update();
                                    resolve();
                                });
                            });
                        });

                        // Wait for all program updates to complete
                        Promise.all(update_promises).then(() => {
                            // --- Client-Side Modification Ends Here ---

                            frappe.call({
                                method: "ifitwala_ed.curriculum.doctype.course.course.add_course_to_programs",
                                args: {
                                    course: frm.doc.name,
                                    programs: data.programs,
                                    mandatory: data.mandatory, // Still useful for server-side consistency
                                },
                                callback: function (r) {
                                    if (!r.exc) {
                                        // Refresh the related Program docs after the server-side call
                                        data.programs.forEach(program_name => {
                                            frappe.model.remove_from_local_cache("Program", program_name);
                                        });
                                        frm.reload_doc();
                                    }
                                },
                                freeze: true,
                                freeze_message: __("...Adding Course to Programs"),
                            });
                        });
                    }
                },
                __("Add Course to Programs"),
                __("Add")
            );
        } else {
            frappe.msgprint(
                __("This course is already added to the existing programs")
            );
        }
    });
  },
});

// to filter out assessment criteria that have already been picked out in the course.
// BUGS: #2 this filter is still not working properly.  It is not filtering out the already selected assessment criteria.
frappe.ui.form.on("Course Assessment Criteria", {
  assessment_criteria_add: function (frm) {
    frm.fields_dict["assessment_criteria"].grid.get_field("assessment_criteria").get_query = function (doc) {
      var criteria_list = [];
      if (!doc.__islocal) criteria_list.push(doc.name);
      $.each(doc.assessment_criteria, function (idx, val) {
        if (val.assessment_criteria)
          criteria_list.push(val.assessment_criteria);
      });
      return {
        filters: [
          ["Assessment Criteria", "course_group", "=", frm.doc.course_group], 
          ["Assessment Criteria", "name", "not in", criteria_list]
        ],
      };
    };
  },
});

let get_programs_without_course = function (course) {
  return frappe.call({
    type: "GET",
    method:
      "ifitwala_ed.curriculum.doctype.course.course.get_programs_without_course",
    args: { course: course },
  });
};
