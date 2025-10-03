// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.js

// Helpers

function canFetchStudents(frm) {
	const source = frm.doc.get_students_from;
	if (source === 'Program Enrollment') {
		return Boolean(frm.doc.program && frm.doc.academic_year);
	}
	if (source === 'Cohort') {
		return Boolean(frm.doc.student_cohort);
	}
	return false;
}

frappe.ui.form.on('Program Enrollment Tool', {
	refresh(frm) {
		frm.disable_save();

		frm.set_query('academic_year', () => ({ query: 'ifitwala_ed.schedule.doctype.program_enrollment_tool.program_enrollment_tool.academic_year_link_query' }));
		frm.set_query('new_academic_year', () => ({ query: 'ifitwala_ed.schedule.doctype.program_enrollment_tool.program_enrollment_tool.academic_year_link_query' }));

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

	get_students_from(frm) {
		toggle_filter_fields(frm);
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
