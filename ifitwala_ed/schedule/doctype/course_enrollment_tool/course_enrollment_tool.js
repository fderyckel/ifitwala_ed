// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt


function show_add_students_button(frm) {
	if (frm.doc.program && frm.doc.academic_year && frm.doc.course) {
		if (!frm.custom_buttons_added) {
			frm.add_custom_button(__("Add Eligible Students"), function () {
				// guard clauses
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
						page_len: 50,                               // keep response lean; adjust if needed
						filters: {
							program: frm.doc.program,
							academic_year: frm.doc.academic_year,
							course: frm.doc.course,
							term: frm.doc.term
						}
					},
					callback: function (r) {
						let eligible = r.message || [];

						// Hide students already in the grid
						const existing = (frm.doc.students || []).map(row => row.student);
						eligible = eligible.filter(([id]) => !existing.includes(id));

						if (!eligible.length) {
							frappe.msgprint(__("All eligible students are already listed."));
							return;
						}

						// Build HTML table string
						let html = `
							<div class="table-responsive">
								<table class="table table-bordered table-hover mb-0">
									<thead class="table-light">
										<tr>
											<th>${__("Full Name")}</th>
											<th style="width:90px;text-align:center;">
												<input type="checkbox" id="select-all">
												<span class="ms-1">${__("All")}</span>
											</th>
										</tr>
									</thead>
									<tbody>`;
						eligible.forEach(([id, label, pe]) => {
							html += `
								<tr>
									<td>${frappe.utils.escape_html(label)}</td>
									<td class="text-center">
										<input type="checkbox" class="student-check"
											data-student="${frappe.utils.escape_html(id)}"
											data-label="${frappe.utils.escape_html(label)}"
											data-pe="${frappe.utils.escape_html(pe || "")}">
									</td>
								</tr>`;
						});
						html += `</tbody></table></div>`;

						// Create dialog
						const d = new frappe.ui.Dialog({
							title: __("Select Eligible Students"),
							fields: [
								{ fieldtype: "HTML", fieldname: "matrix" }
							],
							primary_action_label: __("Add Selected"),
							primary_action() {
								const selected = d.$wrapper.find(".student-check:checked");
								selected.each(function () {
									const $el = $(this);
									const row = frm.add_child("students");
									row.student = $el.data("student");
									row.student_name = $el.data("label");
									row.program_enrollment = $el.data("pe");
								});
								frm.refresh_field("students");
								d.hide();
							}
						});

						// Inject table HTML
						d.get_field("matrix").$wrapper.html(html);

						// Hook up Select-All toggle
						d.$wrapper.find("#select-all").on("change", function () {
							const checked = $(this).is(":checked");
							d.$wrapper.find(".student-check").prop("checked", checked);
						});

						d.show();
					}
				});
			});
			frm.custom_buttons_added = true;
		}
	}
}; 

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

	refresh: function(frm) {
		// Immediate red button to clear all fields
		frm.add_custom_button(__("Clear All Fields"), function () {
			const fields_to_clear = ["program", "academic_year", "term", "course"];
			fields_to_clear.forEach(field => frm.set_value(field, null));
			frm.clear_table("students");
			frm.refresh_fields();
			frm.custom_buttons_added = false; 
		}).addClass("btn-danger");
	}, 

	program: function(frm) {
		frm.set_value("academic_year", null);
		show_add_students_button(frm);
	},

	academic_year: function(frm) {
		show_add_students_button(frm);
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
	},

	course: async function(frm) {
		show_add_students_button(frm);
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