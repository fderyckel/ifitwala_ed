// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// make the field appear whenever *no* program is chosen
function toggle_school_schedule_field(frm) {
    const need_sched = !frm.doc.program;   // ← removed extra test
    frm.set_df_property("school_schedule", "hidden", !need_sched);
    frm.set_df_property("school_schedule", "reqd",  need_sched);
    if (!need_sched) frm.set_value("school_schedule", null);
}

// Helper function to build student filter payload
function get_student_filters(frm) {
	return {
		academic_year: frm.doc.academic_year,
		group_based_on: frm.doc.group_based_on,
		term: frm.doc.term,
		program: frm.doc.program,
		cohort: frm.doc.cohort,
		course: frm.doc.course,
		student_group: frm.doc.name,
	};
}

// run whenever these change
["academic_year", "program", "group_based_on"].forEach(f =>
    frappe.ui.form.on("Student Group", f, frm => toggle_school_schedule_field(frm))
);

// ── Form events ──────────────────────────────────────────────────────────────

frappe.ui.form.on("Student Group", {
	onload: function (frm) {
		//run the toggle once the form is rendered, and when fields change
		toggle_school_schedule_field(frm);

		frm.add_fetch("student", "student_full_name", "student_name");

		frm.set_query("term", function () {
			return {
				filters: {
					academic_year: frm.doc.academic_year,
				},
			};
		});

		// Set student field query for single selection inside the child table
		if (!frm.__islocal) {
			frm.set_query("student", "students", function () {
				return {
					query: "ifitwala_ed.schedule.doctype.student_group.student_group.fetch_students",
					filters: get_student_filters(frm),
				};
			});
		}

		frm.set_query("school_schedule", () => {
			// Show schedules linked to the selected Academic Year
			// AND whose school is either the AY.school or an ancestor thereof
			return {
				query: "ifitwala_ed.schedule.doctype.student_group.student_group.schedule_picker_query",
				filters: {
					academic_year: frm.doc.academic_year
				}
			};
		});	
	},

	refresh: function (frm) {
		// Add buttons
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__('Open Student Cards'), () => {
				frappe.route_options = { student_group: frm.doc.name };
				frappe.set_route('student_group_cards');
			});

			if (!in_list(frappe.user_roles, "Student")) {
				frm.add_custom_button(
					__("Add a session"),
					function () {
						frappe.route_options = {
							event_category: "Course",
							event_type: "Private",
							reference_type: "Student Group",
							reference_name: frm.doc.name,
						};
						frappe.set_route("List", "School Event");
					}
				);
			}
		}

		// Setup "Add Multiple Students" only if not Other/Activity
		if (!["Other", "Activity"].includes(frm.doc.group_based_on)) {
			const grid = frm.fields_dict["students"].grid;

			if (!grid.multiple_add_setup_done) {
				grid.set_multiple_add("student", function (selected_students) {
					const existing = frm.doc.students.map(row => row.student);
					let max_roll_no = Math.max(0, ...frm.doc.students.map(row => row.group_roll_number || 0));

					selected_students.forEach(name => {
						if (!in_list(existing, name)) {
							const row = frm.add_child("students");
							row.student = name;
							row.group_roll_number = ++max_roll_no;
						}
					});

					frm.refresh_field("students");
					frm.save();
				});

				grid.get_field("student").get_query = function () {
					return {
						query: "ifitwala_ed.schedule.doctype.student_group.student_group.fetch_students",
						filters: get_student_filters(frm),
					};
				};

				grid.multiple_add_setup_done = true;
			}
		}
	},

	validate(frm) {
		if (frm.doc.__unsaved && frm.doc.student_group_schedule?.length) {
			frappe.call({
				method: "ifitwala_ed.schedule.schedule_utils.check_slot_conflicts",
				args: { group_doc: frm.doc },
				callback(r) {
					if (Object.keys(r.message || {}).length) {
						frappe.msgprint({
							title: __("Potential Conflicts"),
							message: `<pre>${JSON.stringify(r.message, null, 2)}</pre>`,
							indicator: "orange",
						});
					}
				},
			});
		}
	},  

	program: function (frm) {
		if (frm.doc.program) {
			frm.set_query("course", function () {
				return {
					query: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_program_courses",
					filters: {
						program: frm.doc.program,
					},
				};
			});
		}
	},

	group_based_on: function (frm) {
		frm.set_df_property("program", "reqd", 0);
		frm.set_df_property("course", "reqd", 0);
		frm.set_df_property("cohort", "reqd", 0);

		if (frm.doc.group_based_on === "Cohort") {
			frm.doc.course = null;
			frm.set_df_property("cohort", "reqd", 1);
		} else if (frm.doc.group_based_on === "Course") {
			frm.set_df_property("course", "reqd", 1);
		}
	},

	get_students: function (frm) {
		if (["Other", "Activity"].includes(frm.doc.group_based_on)) {
			frappe.msgprint(__("Select students manually for Activity or Other based groups."));
			return;
		}

		if (frm.doc.academic_year) {
			let student_list = [];
			let max_roll_no = 0;

			$.each(frm.doc.students, function (i, d) {
				student_list.push(d.student);
				if (d.group_roll_number > max_roll_no) {
					max_roll_no = d.group_roll_number;
				}
			});

			frappe.call({
				method: "ifitwala_ed.schedule.doctype.student_group.student_group.get_students",
				args: get_student_filters(frm),
				callback: function (r) {
					if (r.message) {
						$.each(r.message, function (i, d) {
							if (!in_list(student_list, d.student)) {
								const row = frm.add_child("students");
								row.student = d.student;
								row.student_name = d.student_name;
								row.active = d.active || 0;
								row.group_roll_number = ++max_roll_no;
							}
						});
						refresh_field("students");
						frm.save();
					} else {
						frappe.msgprint(__("No new students found or Student Group already updated."));
					}
				}
			});
		} else {
			frappe.msgprint(__("Please select an Academic Year before fetching students."));
		}
	}, 

	add_blocks(frm) {			
		if (!frm.doc.school_schedule) {
			frappe.msgprint(__('Select a School Schedule first.'));
			return;
		}
		frappe.call({
			method: 'ifitwala_ed.schedule.schedule_utils.fetch_block_grid',
			args: {
				schedule_name: frm.doc.school_schedule,
				sg: frm.doc.name
			},
			callback(r) {
				build_matrix_dialog(frm, r.message);
			}
		});
	}
});

frappe.ui.form.on("Student Group Instructor", {
	instructors_add: function (frm) {
		frm.fields_dict["instructors"].grid.get_field("instructor").get_query =
			function (doc) {
				let instructor_list = [];
				$.each(doc.instructors, function (idx, val) {
					instructor_list.push(val.instructor);
				});
				return { filters: [["Instructor", "name", "not in", instructor_list]] };
			};
	},
});

// ── Dialog builder (unchanged except parseInt) ──────────────────────
function build_matrix_dialog(frm, data) {
	const d = new frappe.ui.Dialog({
		title: __('Quick Add Schedule Blocks'),
		size: 'large',
		primary_action_label: __('Add Selected'),
		primary_action() {
			apply_matrix_selection(frm, d);
			d.hide();
		}
	});

	let html = '<table class="table table-bordered"><thead><tr><th></th>';
	data.days.forEach(day => html += `<th class="text-center">Day ${day}</th>`);
	html += '</tr></thead><tbody>';

	const maxBlocks = Math.max(...data.days.map(d => data.grid[d].length));

	for (let row = 0; row < maxBlocks; row++) {
		html += `<tr><th class="text-center">Block ${row + 1}</th>`;
		data.days.forEach(day => {
			const blk = data.grid[day][row];
			if (blk) {
				const id = `d${day}b${blk.block}`;
				html += `
					<td>
						<div class="form-check">
							<input type="checkbox" id="${id}" class="form-check-input"/>
						</div>
						<input class="form-control form-control-xs mt-1 room" placeholder="Room"/>
						<select class="form-control form-control-xs mt-1 instructor">
							<option value=""></option>
							${data.instructors.map(i=>`<option value="${i.value}">${i.label}</option>`).join('')}
						</select>
					</td>`;
			} else {
				html += '<td class="bg-light"></td>';
			}
		});
		html += '</tr>';
	}
	html += '</tbody></table>';

	d.$body.html(html);
	d.show();
}

function apply_matrix_selection(frm, dialog) {
	const cells = dialog.$wrapper.find('input[type=checkbox]:checked').closest('td');
	cells.each(function() {
		const cell = $(this);
		const ids = cell.find('input[type=checkbox]').attr('id').match(/d(\d+)b(\d+)/);
		const rotation_day = parseInt(ids[1]);
		const block_number = parseInt(ids[2]);

		frm.add_child('student_group_schedule', {
			rotation_day,
			block_number,
			location: cell.find('input.room').val(),
			instructor: cell.find('select.instructor').val()
		});
	});
	frm.refresh_field('student_group_schedule');
	frm.dirty();
}
