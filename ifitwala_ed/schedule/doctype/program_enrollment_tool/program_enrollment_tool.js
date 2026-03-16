// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/schedule/doctype/program_enrollment_tool/program_enrollment_tool.js

function canFetchStudents(frm) {
	const source = frm.doc.get_students_from;
	if (source === 'Program Enrollment') {
		return Boolean(frm.doc.program_offering && frm.doc.target_academic_year);
	}
	if (source === 'Cohort') {
		return Boolean(frm.doc.student_cohort);
	}
	return false;
}

function hasDestinationContext(frm) {
	return Boolean(frm.doc.new_program_offering && frm.doc.new_target_academic_year);
}

function hasStudents(frm) {
	return Boolean((frm.doc.students || []).length);
}

function prettyCountLabel(key) {
	return String(key || '')
		.split('_')
		.map(part => part.charAt(0).toUpperCase() + part.slice(1))
		.join(' ');
}

function runToolAction(frm, method) {
	if (!hasDestinationContext(frm)) {
		frappe.msgprint(__('Please choose a destination Program Offering and destination Academic Year first.'));
		return;
	}
	if (!hasStudents(frm)) {
		frappe.msgprint(__('Please load or add students first.'));
		return;
	}

	frappe.call({
		doc: frm.doc,
		method,
		freeze: true
	});
}

frappe.ui.form.on('Program Enrollment Tool', {
	refresh(frm) {
		frm.disable_save();
		frm.clear_custom_buttons();

		if (!frm.__pe_rt_bound) {
			frappe.realtime.on('program_enrollment_tool', data => {
				frappe.hide_msgprint(true);
				frappe.show_progress(
					data.action_label || __('Processing'),
					data.progress?.[0] || 0,
					data.progress?.[1] || 0
				);
			});

			frappe.realtime.on('program_enrollment_tool_done', summary => {
				const counts = Object.entries(summary?.counts || {})
					.map(([key, value]) => `${prettyCountLabel(key)}: ${value}`)
					.join(', ');
				const detailsLink = summary?.details_link
					? `<br><a href="${summary.details_link}" target="_blank">${__('Download details CSV')}</a>`
					: '';
				frappe.msgprint({
					title: summary?.title || __('Batch Finished'),
					message: `${counts}${detailsLink}`,
					indicator: 'green'
				});
			});

			frm.__pe_rt_bound = true;
		}

		frm.set_query('target_academic_year', () => ({
			query: 'ifitwala_ed.schedule.doctype.program_enrollment_tool.program_enrollment_tool.program_offering_target_ay_query',
			filters: { program_offering: frm.doc.program_offering }
		}));

		frm.set_query('new_target_academic_year', () => ({
			query: 'ifitwala_ed.schedule.doctype.program_enrollment_tool.program_enrollment_tool.program_offering_target_ay_query',
			filters: { program_offering: frm.doc.new_program_offering }
		}));

		toggleFilterFields(frm);
		addTableToolbar(frm);
		addActionButtons(frm);
	},

	get_students_from(frm) {
		toggleFilterFields(frm);
	},

	program_offering(frm) {
		frm.set_value('target_academic_year', null);
	},

	new_program_offering(frm) {
		frm.set_value('new_target_academic_year', null);
	},

	get_students(frm) {
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
					highlightTargetCollisions(frm);
					frm.refresh();
				}
			}
		});
	},

	enroll_students(frm) {
		runToolAction(frm, 'prepare_requests');
	}
});

function addActionButtons(frm) {
	if (!hasDestinationContext(frm) || !hasStudents(frm)) {
		return;
	}

	frm.add_custom_button(__('Validate Requests'), () => runToolAction(frm, 'validate_requests'), __('Actions'));
	frm.add_custom_button(__('Approve Valid Requests'), () => runToolAction(frm, 'approve_requests'), __('Actions'));
	frm.add_custom_button(__('Materialize Requests'), () => runToolAction(frm, 'materialize_requests'), __('Actions'));
}

function addTableToolbar(frm) {
	const grid = frm.get_field('students').grid;
	if (grid.__programEnrollmentToolToolbarBound) {
		return;
	}

	grid.add_custom_button(__('Select All'), () => {
		grid.grid_rows.forEach(row => {
			row.doc.__checked = 1;
		});
		grid.refresh();
	});

	grid.add_custom_button(__('Clear Table'), () => {
		frm.set_value('students', []);
	});

	grid.add_custom_button(__('Add Student…'), () => {
		frappe.prompt(
			[{ fieldtype: 'Link', label: 'Student', fieldname: 'student', options: 'Student', reqd: 1 }],
			values => {
				frappe.db.get_value('Student', values.student, ['student_full_name', 'cohort']).then(({ message }) => {
					grid.add_new_row({
						student: values.student,
						student_name: message.student_full_name,
						student_cohort: message.cohort
					});
					grid.refresh();
				});
			}
		);
	});

	grid.__programEnrollmentToolToolbarBound = true;
}

function highlightTargetCollisions(frm) {
	const grid = frm.get_field('students').grid;
	grid.grid_rows.forEach(row => {
		if (row.doc.already_enrolled) {
			row.wrapper.css({ background: '#ffebe9' });
		} else {
			row.wrapper.css({ background: '' });
		}
	});
}

function toggleFilterFields(frm) {
	const source = frm.doc.get_students_from;

	frm.toggle_display('program_offering', false);
	frm.toggle_display('target_academic_year', false);
	frm.toggle_display('student_cohort', false);

	if (source === 'Program Enrollment') {
		frm.toggle_display('program_offering', true);
		frm.toggle_display('target_academic_year', true);
		frm.toggle_display('student_cohort', true);
	} else if (source === 'Cohort') {
		frm.toggle_display('student_cohort', true);
	}
}
