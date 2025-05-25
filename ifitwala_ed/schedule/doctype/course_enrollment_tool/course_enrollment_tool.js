// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt


frappe.ui.form.on("Course Enrollment Tool", {
	onload: function(frm) {
		// Set the query for academic year
		frm.set_query("academic_year", function () {
			return {
				query: "ifitwala_ed.schedule.doctype.course_enrollment_tool.course_enrollment_tool.list_academic_years_desc"
			};
		});

		// Filter programs based on user's school
		frappe.call({
			method: "ifitwala_ed.utilities.school_tree.get_descendant_schools",
			args: { user_school: frappe.defaults.get_user_default("school") },
			callback: function(r) {
				window.allowed_schools = r.message || [frappe.defaults.get_user_default("school")];

				frm.set_query("program", function() {
					return {
						filters: {
							school: ["in", window.allowed_schools]
						}
					};
				});
			}
		});
	},

	program: function(frm) {
		frm.set_value("academic_year", null);
	},

	onload_post_render: function(frm) {
		// 1) Server-side query to fetch eligible students for each row
		frm.set_query("student", "students", function(doc, cdt, cdn) {
			return {
				query: "ifitwala_ed.schedule.doctype.course_enrollment_tool.course_enrollment_tool.fetch_eligible_students",
				filters: {
					academic_year: frm.doc.academic_year,
					program: frm.doc.program,
					course: frm.doc.course,
					term: frm.doc.term
				}
			};
		});

		// 2) Client-side filter to prevent duplicate student entries
		frm.fields_dict["students"].grid.get_field("student").get_query = function(doc) {
			const selected_students = (doc.students || []).map(row => row.student).filter(Boolean);
			return {
				filters: [
					["Student", "name", "not in", selected_students]
				]
			};
		};

		// 3) Custom query for Course field to show only courses from selected Program
		frm.set_query("course", function() {
			if (!frm.doc.program) return {};
			return {
				query: "ifitwala_ed.schedule.doctype.course_enrollment_tool.course_enrollment_tool.get_courses_for_program",
				filters: {
					program: frm.doc.program
				}
			};
		});

		// 4) Custom button to add eligible students
		frm.add_custom_button(__("Add Eligible Students"), async function () {
			if (!frm.doc.program || !frm.doc.academic_year || !frm.doc.course) {
				frappe.msgprint(__("Please select Program, Academic Year, and Course first."));
				return;
			}

			frappe.call({
				method: "ifitwala_ed.schedule.doctype.course_enrollment_tool.course_enrollment_tool.fetch_eligible_students",
				args: {
					doctype: "Student",
					txt: "",
					searchfield: "name",
					start: 0,
					page_len: 50,
					filters: {
						program: frm.doc.program,
						academic_year: frm.doc.academic_year,
						course: frm.doc.course,
						term: frm.doc.term
					}
				},
				callback: function(r) {
					const eligible = r.message || [];
					if (eligible.length === 0) {
						frappe.msgprint(__("No eligible students found."));
						return;
					}

					eligible.forEach(([student_id, label, pe_name]) => {
						const row = frm.add_child("students");
						row.student = student_id;
						row.student_name = label;
						row.program_enrollment = pe_name;
					});
					frm.refresh_field("students");
				}
			});
		});
	},

	course: async function(frm) {
		if (!frm.doc.course) {
			frm.set_df_property("term", "hidden", 1);
			return;
		}

		const course = await frappe.db.get_doc("Course", frm.doc.course);
		const is_term_long = !!course.term_long;

		frm.set_df_property("term", "hidden", !is_term_long);

		if (!is_term_long) {
			frm.set_value("term", null);
		}

		frm.set_query("term", function() {
			return {
				filters: {
					academic_year: frm.doc.academic_year || ""
				}
			};
		});
	},

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

		if (!frm.doc.program || !frm.doc.academic_year) {
			frappe.msgprint(__("Please select Program and Academic Year first"));
			return;
		}

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
					frappe.model.set_value(cdt, cdn, "program_enrollment", r.message.name);
				} else {
					frappe.model.set_value(cdt, cdn, "program_enrollment", null);
				}
			}
		});
	}
});