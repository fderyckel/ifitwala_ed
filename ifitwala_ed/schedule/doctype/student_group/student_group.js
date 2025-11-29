// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed.schedule.doctype.student_group.student_group.js

// ── Helper functions ──────────────────────────────────────────────────────────────

function toggle_school_schedule_field(frm) {
	// Show School Schedule when there is NO Program Offering (i.e., non-offering flows like Activity/Other)
	// FIX: do NOT clear school_schedule here (that was causing re-dirty loops)
	const need_sched = !frm.doc.program_offering;
	frm.set_df_property("school_schedule", "hidden", !need_sched);
	frm.set_df_property("school_schedule", "reqd",  need_sched);
}

// Build student filter payload for server calls
function get_student_filters(frm) {
	return {
		program_offering: frm.doc.program_offering,
		academic_year: frm.doc.academic_year,
		group_based_on: frm.doc.group_based_on,
		term: frm.doc.term,
		cohort: frm.doc.cohort,
		course: frm.doc.course,
		student_group: frm.doc.name,
	};
}

// Keep the toggle in sync
["academic_year", "program_offering", "group_based_on"].forEach(f =>
	frappe.ui.form.on("Student Group", f, frm => toggle_school_schedule_field(frm))
);


// ── Form events ──────────────────────────────────────────────────────────────

frappe.ui.form.on("Student Group", {

	onload(frm) {
		// AY scoped to Program Offering spine
		frm.set_query("academic_year", () => ({
			query: "ifitwala_ed.schedule.doctype.student_group.student_group.offering_ay_query",
			filters: { program_offering: frm.doc.program_offering || "" }
		}));

		// School scoped to AY branch or AY∩PO intersection
		frm.set_query("school", () => ({
			query: "ifitwala_ed.schedule.doctype.student_group.student_group.allowed_school_query",
			filters: {
				academic_year: frm.doc.academic_year || "",
				program_offering: frm.doc.program_offering || ""
			}
		}));

		// Course scoped to Program Offering (+ AY/Term windows)
		frm.set_query("course", () => ({
			query: "ifitwala_ed.schedule.doctype.student_group.student_group.offering_course_query",
			filters: {
				program_offering: frm.doc.program_offering || "",
				academic_year: frm.doc.academic_year || "",
				term: frm.doc.term || ""
			}
		}));

		// Term filter by AY
		frm.set_query("term", () => ({ filters: { academic_year: frm.doc.academic_year } }));

		// Child row student query (only after save)
		if (!frm.__islocal) {
			frm.set_query("student", "students", () => ({
				query: "ifitwala_ed.schedule.doctype.student_group.student_group.fetch_students",
				filters: get_student_filters(frm),
			}));
		}

		// School Schedule picker (AY-aware)
		frm.set_query("school_schedule", () => ({
			query: "ifitwala_ed.schedule.doctype.student_group.student_group.schedule_picker_query",
			filters: { academic_year: frm.doc.academic_year }
		}));

		// Instructor constraint on schedule rows
		// FIX: add guard so we don’t reset query every refresh
		if (frm.fields_dict["student_group_schedule"]) {
			const grid = frm.fields_dict["student_group_schedule"].grid;
			const f = grid.get_field("instructor");
			if (f && !f.__set_once) {
				f.get_query = function () {
					const valid = (frm.doc.instructors || []).map(r => r.instructor);
					return { filters: { name: ["in", valid] } };
				};
				f.__set_once = true;
			}
		}

		toggle_school_schedule_field(frm);
		frm.add_fetch("student", "student_full_name", "student_name");
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
					// FIX: removed frm.save(); → auto-save caused "Not Saved" loop
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

	// FIX: clear dependent fields only when user actually changes program_offering
	program_offering(frm) {
		frm.set_value("academic_year", null);
		frm.set_value("school", null);
		frm.set_value("course", null);
		frm.set_value("school_schedule", null); // moved here only
	},

	academic_year(frm) {
		frm.set_value("school", null);
		frm.set_value("course", null);
	},

	group_based_on(frm) {
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
	// Activity / Other groups are manual selection only
	if (["Other", "Activity"].includes(frm.doc.group_based_on)) {
		frappe.msgprint(__("Select students manually for Activity or Other based groups."));
		return;
	}

	// We require an Academic Year (scoped to Program Offering's spine)
	if (!frm.doc.academic_year) {
		frappe.msgprint(__("Please select an Academic Year before fetching students."));
		return;
	}

	// Build existing map to avoid duplicates and track next roll number
	const existing = Array.isArray(frm.doc.students) ? frm.doc.students.map(r => r.student) : [];
	let max_roll_no = Array.isArray(frm.doc.students)
		? Math.max(0, ...frm.doc.students.map(r => r.group_roll_number || 0))
		: 0;

	// Server call (offering-first). Args come from the helper in this file.
	frappe.call({
		method: "ifitwala_ed.schedule.doctype.student_group.student_group.get_students",
		args: get_student_filters(frm),
		callback: function (r) {
			const rows = Array.isArray(r.message) ? r.message : [];
			if (!rows.length) {
				frappe.msgprint(__("No new students found or Student Group already updated."));
				return;
			}

			rows.forEach(d => {
				if (d.student && !existing.includes(d.student)) {
					const row = frm.add_child("students");
					row.student = d.student;
					row.student_name = d.student_name || "";
					row.active = d.active ? 1 : 0;
					row.group_roll_number = ++max_roll_no;
				}
			});

			frm.refresh_field("students");
			// FIX: removed frm.save(); auto-save led to re-triggered “unsaved” flicker
		}
	});
},


	add_blocks(frm) {
		frappe.call({
			method: "ifitwala_ed.schedule.student_group_scheduling.fetch_block_grid",
			args: { schedule_name: frm.doc.school_schedule || null, sg: frm.doc.name },
			callback(r) {
				if (!frm.doc.school_schedule && r.message?.schedule_name) {
					frm.set_value("school_schedule", r.message.schedule_name);
				}
				build_matrix_dialog(frm, r.message);
			}
		});
	},

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


// ── Dialog builder (unchanged except parseInt + no dirty) ──────────────────────

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
						<input class="form-control form-control-xs mt-1 location" placeholder="Room"/>
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
		const rotation_day = parseInt(ids[1], 10);
		const block_number = parseInt(ids[2], 10);

		frm.add_child('student_group_schedule', {
			rotation_day,
			block_number,
			location: cell.find('input.location').val(),
			instructor: cell.find('select.instructor').val()
		});
	});
	frm.refresh_field('student_group_schedule');
	// FIX: removed explicit frm.dirty(); adding children already marks unsaved
}
