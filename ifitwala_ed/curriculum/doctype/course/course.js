// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/curriculum/doctype/course/course.js

frappe.ui.form.on("Course", {
	setup(frm) {
		frm.add_fetch("team", "school", "school");

		const table = frm.fields_dict.assessment_criteria;
		if (!table || !table.grid) {
			// Field renamed/removed – fail quietly
			return;
		}

		table.grid
			.get_field("assessment_criteria")
			.get_query = function (doc, cdt, cdn) {
				const selected = (doc.assessment_criteria || [])
					.map(row => row.assessment_criteria)
					.filter(v => !!v);

				const filters = [];

				// Only filter by course_group if set; otherwise don't block everything.
				if (frm.doc.course_group) {
					filters.push(["Assessment Criteria", "course_group", "=", frm.doc.course_group]);
				}

				if (selected.length) {
					filters.push(["Assessment Criteria", "name", "not in", selected]);
				}

				return { filters };
			};
	},


  onload: function (frm) {
		prefill_course_default_school(frm);
	},

  refresh: function (frm) {
		if (frm.is_new() || !frm.doc.name) return;
    if (!cur_frm.doc.__islocal) {
      frm.add_custom_button(
        __("Add to Programs"),
        function () {
          frm.trigger("add_course_to_programs");
        }
      );
    }

		frm.add_custom_button(__("View Course Plans"), () => {
			frappe.set_route("List", "Course Plan", { course: frm.doc.name });
		}, __("Units"));

		frm.add_custom_button(__("View Unit Plans"), () => {
			frappe.set_route("List", "Unit Plan", { course: frm.doc.name });
		}, __("Units"));

    // to only suggest grade scale that are submitted (not cancel nor draft)
    frm.set_query("default_grade_scale", function () {
      return {
        filters: {
          docstatus: 1,
        },
      };
    });

		refresh_course_website_banner(frm);
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
              get_data: function () {
                return r.message;
              },
            },
            {
              fieldtype: "Check",
              label: __("Is Mandatory"),
              fieldname: "mandatory",
            },
          ],
          function (data) {
            frappe.call({
              method:
                "ifitwala_ed.curriculum.doctype.course.course.add_course_to_programs",
              args: {
                course: frm.doc.name,
                programs: data.programs,
                mandatory: data.mandatory,
              },
              callback: function (r) {
                if (!r.exc) {
                  frm.reload_doc();
                }
              },
              freeze: true,
              freeze_message: __("...Adding Course to Programs"),
            });
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

async function refresh_course_website_banner(frm) {
	if (!frm.dashboard || !frm.dashboard.set_headline) return;

	const warnings = [];
	if (frm.doc.is_published && !frm.doc.school) {
		warnings.push(__("Course is published but has no School, so no public website profile can be prepared."));
	}

	if (frm.doc.is_published && frm.doc.school) {
		const profiles = await frappe.db.get_list("Course Website Profile", {
			filters: { course: frm.doc.name },
			fields: ["name", "status"],
			limit: 20
		});
		const publishedProfiles = (profiles || []).filter((row) => row.status === "Published");
		if (!profiles || profiles.length === 0) {
			warnings.push(__("Course is published but no Website Profile has been prepared yet."));
		} else if (publishedProfiles.length === 0) {
			warnings.push(__("Course website profile is prepared, but not published yet."));
		}
	}

	if (warnings.length) {
		const html = warnings.map((msg) => `• ${frappe.utils.escape_html(msg)}`).join("<br>");
		frm.dashboard.set_headline(`<span class="text-warning">${html}</span>`);
	} else {
		frm.dashboard.set_headline("");
	}
}

function prefill_course_default_school(frm) {
	if (!frm.is_new() || frm.doc.school) return;

	frappe.call({
		method: "ifitwala_ed.utilities.school_tree.get_user_default_school",
		callback: function (r) {
			const school = r && r.message;
			if (school && !frm.doc.school) {
				frm.set_value("school", school);
			}
		}
	});
}




// ---- server calls ----

let get_programs_without_course = function (course) {
  return frappe.call({
    type: "GET",
    method:
      "ifitwala_ed.curriculum.doctype.course.course.get_programs_without_course",
    args: { course: course },
  });
};

// ---- helpers ----
