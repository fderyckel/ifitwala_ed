// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

function show_add_students_button(frm) {
	// Require offering + AY + course
	if (frm.doc.program_offering && frm.doc.academic_year && frm.doc.course) {
		if (!frm.custom_buttons_added) {
			frm.add_custom_button(__("Add Eligible Students"), function () {
				if (!frm.doc.program_offering || !frm.doc.academic_year || !frm.doc.course) {
					frappe.msgprint(__("Please select Program Offering, Academic Year, and Course first."));
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
							program_offering: frm.doc.program_offering,
							academic_year: frm.doc.academic_year,
							course: frm.doc.course,
							term: frm.doc.term
						}
					},
					callback: function (r) {
						let eligible = r.message || [];
						const existing = (frm.doc.students || []).map(row => row.student);
						eligible = eligible.filter(([id]) => !existing.includes(id));

						if (!eligible.length) {
							frappe.msgprint(__("All eligible students are already listed."));
							return;
						}

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

						const d = new frappe.ui.Dialog({
							title: __("Select Eligible Students"),
							fields: [{ fieldtype: "HTML", fieldname: "matrix" }],
							primary_action_label: __("Add Selected"),
							primary_action() {
								d.$wrapper.find(".student-check:checked").each(function () {
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

						d.get_field("matrix").$wrapper.html(html);
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
}

frappe.ui.form.on("Course Enrollment Tool", {
	onload(frm) {
		// Academic Year query — scoped to offering (DESC)
		frm.set_query("academic_year", function () {
			return {
				query: "ifitwala_ed.schedule.doctype.course_enrollment_tool.course_enrollment_tool.list_offering_academic_years_desc",
				filters: { program_offering: frm.doc.program_offering || "" }
			};
		});

		// Program is derived from Program Offering → make it read-only once set
		if (frm.doc.program_offering && frm.doc.program) {
			frm.set_df_property("program", "read_only", 1);
		}

		// Course query — from Program Offering Courses
		frm.set_query("course", function () {
			if (!frm.doc.program_offering) return {};
			return {
				query: "ifitwala_ed.schedule.doctype.course_enrollment_tool.course_enrollment_tool.get_courses_for_offering",
				filters: {
					program_offering: frm.doc.program_offering,
					academic_year: frm.doc.academic_year || ""
				}
			};
		});
	},

	refresh(frm) {
		// Clear All
		frm.add_custom_button(__("Clear All Fields"), function () {
			const fields_to_clear = ["program_offering", "program", "academic_year", "term", "course"];
			fields_to_clear.forEach(f => frm.set_value(f, null));
			frm.clear_table("students");
			frm.refresh_fields();
			frm.custom_buttons_added = false;
			frm.set_df_property("program", "read_only", 0);
		}).addClass("btn-danger");

		// 👇 Style the DocField Button: add_course
		const $btn = frm.fields_dict.add_course?.$wrapper?.find("button");
		if ($btn && $btn.length) {
			$btn.removeClass("btn-default btn-secondary").addClass("btn-primary");
		}
	},

	// New: when Program Offering changes → derive & lock program, clear dependent fields
	async program_offering(frm) {
		if (!frm.doc.program_offering) {
			frm.set_value("program", null);
			frm.set_value("school", null);
			frm.set_df_property("program", "read_only", 0);
			return;
		}
		const po = await frappe.db.get_doc("Program Offering", frm.doc.program_offering);
		frm.set_value("program", po.program || null);
		frm.set_value("school", po.school || null);
		frm.set_df_property("program", "read_only", 1);

		// Clear dependents
		["academic_year", "term", "course"].forEach(f => frm.set_value(f, null));
		frm.clear_table("students");
		frm.refresh_fields();

		show_add_students_button(frm);
	},

	// Keep old handlers but now they rely on offering as the key
	program(frm) {
		// program is derived; don’t clear AY here anymore
		show_add_students_button(frm);
	},

	academic_year(frm) {
		show_add_students_button(frm);
	},

	onload_post_render(frm) {
		// Server-side query for Student link in grid — now uses offering
		frm.set_query("student", "students", function (doc) {
			return {
				query: "ifitwala_ed.schedule.doctype.course_enrollment_tool.course_enrollment_tool.fetch_eligible_students",
				filters: {
					program_offering: frm.doc.program_offering,
					academic_year: frm.doc.academic_year,
					course: frm.doc.course,
					term: frm.doc.term
				}
			};
		});

		// Client-side duplicate guard
		frm.fields_dict["students"].grid.get_field("student").get_query = function (doc) {
			const selected = (doc.students || []).map(r => r.student).filter(Boolean);
			return { filters: [["Student", "name", "not in", selected]] };
		};

		// Course query (again) in case onload_post_render runs before onload
		frm.set_query("course", function () {
			if (!frm.doc.program_offering) return {};
			return {
				query: "ifitwala_ed.schedule.doctype.course_enrollment_tool.course_enrollment_tool.get_courses_for_offering",
				filters: {
					program_offering: frm.doc.program_offering,
					academic_year: frm.doc.academic_year || ""
				}
			};
		});
	},

	async course(frm) {
		show_add_students_button(frm);
		if (!frm.doc.course) {
			frm.set_df_property("term", "hidden", 1);
			return;
		}
		const course = await frappe.db.get_doc("Course", frm.doc.course);
		const is_term_long = !!course.term_long;
		frm.set_df_property("term", "hidden", !is_term_long);
		if (!is_term_long) frm.set_value("term", null);

		// Term filter limited to selected AY
		frm.set_query("term", function () {
			return { filters: { academic_year: frm.doc.academic_year || "" } };
		});
	},

	add_course(frm) {
		frappe.call({
			doc: frm.doc,
			method: "add_course_to_program_enrollment",
			callback: function (r) {
				if (!r.exc) frm.reload_doc();
			}
		});
	}
});

frappe.ui.form.on("Course Enrollment Tool Student", {
	// Resolve PE by (student, program_offering, academic_year)
	student(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		if (!frm.doc.program_offering || !frm.doc.academic_year) {
			frappe.msgprint(__("Please select Program Offering and Academic Year first"));
			return;
		}
		frappe.call({
			method: "frappe.client.get_value",
			args: {
				doctype: "Program Enrollment",
				fieldname: "name",
				filters: {
					student: row.student,
					program_offering: frm.doc.program_offering,
					academic_year: frm.doc.academic_year,
					archived: 0
				}
			},
			callback: function (r) {
				const name = r?.message?.name || null;
				frappe.model.set_value(cdt, cdn, "program_enrollment", name);
			}
		});
	}
});
