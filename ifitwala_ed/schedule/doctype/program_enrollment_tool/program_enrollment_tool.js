// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.js

// Reuse canonical AY query on Program Enrollment, scoped by Program → School.
// We pass { school } into program_enrollment.get_academic_years which already
// implements school + ancestor fallback (no duplication = no drift).

// Helpers
async function resolveSchoolFromProgram(program) {
	if (!program) return null;
	const { message } = await frappe.db.get_value('Program', program, 'school');
	return message ? message.school : null;
}

function setAYQueryForField(frm, fieldname, school) {
	frm.set_query(fieldname, () => {
		if (!school) {
			// Keep empty until a Program is chosen to avoid confusing “all AYs” list.
			return { filters: { name: '__never__' } };
		}
		return {
			query: 'ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_academic_years',
			filters: { school }
		};
	});
}

async function initAYQueries(frm) {
	// Initialize based on any prefilled values (route defaults, etc.)
	if (frm.doc.program) {
		const school = await resolveSchoolFromProgram(frm.doc.program);
		setAYQueryForField(frm, 'academic_year', school);
	} else {
		setAYQueryForField(frm, 'academic_year', null);
	}

	if (frm.doc.new_program) {
		const school = await resolveSchoolFromProgram(frm.doc.new_program);
		setAYQueryForField(frm, 'new_academic_year', school);
	} else {
		setAYQueryForField(frm, 'new_academic_year', null);
	}
}

function canFetchStudents(frm) {
	const source = frm.doc.get_students_from;
	if (source === 'Program Enrollment') {
		return Boolean(frm.doc.program && frm.doc.academic_year);
	}
	if (source === 'Cohort') {
		return Boolean(frm.doc.student_cohort);
	}
	// Unsupported options are guarded server-side, but block early here too
	return false;
}

frappe.ui.form.on('Program Enrollment Tool', {
	refresh(frm) {
		frm.disable_save();

		// idempotent realtime bindings
		if (!frm.__pe_rt_bound) {
			frappe.realtime.on('program_enrollment_tool', data => {
				frappe.hide_msgprint(true);
				frappe.show_progress(__('Enrolling students'), data.progress[0], data.progress[1]);
			});

			frappe.realtime.on('program_enrollment_tool_done', summary => {
				const msg = `Created: ${summary.created}, Skipped: ${summary.skipped}, Failed: ${summary.failed}`;
				if (summary.fail_link) {
					const url = summary.fail_link; // server returns full file_url
					frappe.msgprint({
						title: __('Batch Finished'),
						message: `${msg}<br><a href="${url}" target="_blank">Download failures CSV</a>`,
						indicator: 'green'
					});
				} else {
					frappe.msgprint(msg);
				}
				frm.set_value('students', []);
			});

			frm.__pe_rt_bound = true;
		}

		// Field visibility
		toggle_filter_fields(frm);

		// Table toolbar
		add_table_toolbar(frm);
	},

	async onload(frm) {
		// Make AY fields inert until Program is known, or initialize if prefilled
		await initAYQueries(frm);
	},

	get_students_from(frm) {
		toggle_filter_fields(frm);
	},

	// When Program changes, scope Academic Year options based on Program.school
	async program(frm) {
		frm.set_value('academic_year', null);
		const school = await resolveSchoolFromProgram(frm.doc.program);
		setAYQueryForField(frm, 'academic_year', school);
	},

	// When New Program changes, scope New Academic Year similarly
	async new_program(frm) {
		frm.set_value('new_academic_year', null);
		const school = await resolveSchoolFromProgram(frm.doc.new_program);
		setAYQueryForField(frm, 'new_academic_year', school);
	},

	get_students(frm) {
		// Guardrails per source
		if (!canFetchStudents(frm)) {
			frappe.msgprint(__('Please complete the required filters for the selected source first.'));
			return;
		}

		frm.set_value('students', []);
		frappe.call({
			doc: frm.doc,
			method: 'get_students',
			callback(r) {
				if (r.message) {
					frm.set_value('students', r.message);
					highlight_duplicates(frm);
				}
			}
		});
	},

	enroll_students(frm) {
		frappe.call({
			doc: frm.doc,
			method: 'enroll_students',
			freeze: true,
			callback() {
				// summary comes via realtime
			}
		});
	}
});

// -------------------------
// Helper Functions
// -------------------------
function add_table_toolbar(frm) {
	const grid = frm.get_field('students').grid;

	// Select All
	grid.add_custom_button(__('Select All'), () => {
		grid.grid_rows.forEach(r => r.doc.__checked = 1);
		grid.refresh();
	});

	// Clear
	grid.add_custom_button(__('Clear Table'), () => {
		frm.set_value('students', []);
	});

	// Add Student manually
	grid.add_custom_button(__('Add Student…'), () => {
		frappe.prompt([
			{ fieldtype: 'Link', label: 'Student', fieldname: 'student', options: 'Student', reqd: 1 }
		], values => {
			frappe.db.get_value('Student', values.student, ['student_full_name','cohort']).then(({ message }) => {
				grid.add_new_row({
					student: values.student,
					student_name: message.student_full_name,
					student_cohort: message.cohort
				});
				grid.refresh();
			});
		});
	});
}

function highlight_duplicates(frm) {
	const grid = frm.get_field('students').grid;
	grid.grid_rows.forEach(row => {
		if (row.doc.already_enrolled) {
			row.wrapper.css({ background: '#ffebe9' });
		}
	});
}

function toggle_filter_fields(frm) {
	const source = frm.doc.get_students_from;

	frm.toggle_display('program', false);
	frm.toggle_display('academic_year', false);
	frm.toggle_display('student_cohort', false);

	if (source === 'Program Enrollment') {
		frm.toggle_display('program', true);
		frm.toggle_display('academic_year', true);
		frm.toggle_display('student_cohort', true); // optional cohort filter
	} else if (source === 'Cohort') {
		frm.toggle_display('student_cohort', true);
	}
}
