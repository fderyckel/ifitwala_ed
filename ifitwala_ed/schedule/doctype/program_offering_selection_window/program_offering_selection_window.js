// Copyright (c) 2026, Francois de Ryckel and contributors
// For license information, please see license.txt

function hasStudents(frm) {
	return Boolean((frm.doc.students || []).length);
}

function toggleSourceFields(frm) {
	const sourceMode = frm.doc.source_mode || 'Program Enrollment';

	frm.toggle_display('source_program_offering', sourceMode === 'Program Enrollment');
	frm.toggle_display('source_academic_year', sourceMode === 'Program Enrollment');
	frm.toggle_display('source_student_cohort', sourceMode === 'Program Enrollment' || sourceMode === 'Cohort');
}

function callWindowAction(frm, method) {
	if (frm.is_new()) {
		frappe.msgprint(__('Please save this selection window first.'));
		return;
	}
	frappe.call({
		doc: frm.doc,
		method,
		freeze: true,
		callback: () => frm.reload_doc(),
	});
}

frappe.ui.form.on('Program Offering Selection Window', {
	refresh(frm) {
		toggleSourceFields(frm);

		frm.set_query('academic_year', () => ({
			query: 'ifitwala_ed.schedule.doctype.program_enrollment_tool.program_enrollment_tool.program_offering_target_ay_query',
			filters: { program_offering: frm.doc.program_offering },
		}));

		frm.set_query('source_academic_year', () => ({
			query: 'ifitwala_ed.schedule.doctype.program_enrollment_tool.program_enrollment_tool.program_offering_target_ay_query',
			filters: { program_offering: frm.doc.source_program_offering },
		}));

		frm.clear_custom_buttons();
		if (!frm.is_new()) {
			frm.add_custom_button(__('Load Students'), () => callWindowAction(frm, 'load_students'));
			frm.add_custom_button(__('Prepare Requests'), () => callWindowAction(frm, 'prepare_requests'));

			if (frm.doc.status === 'Open') {
				frm.add_custom_button(__('Close Window'), () => callWindowAction(frm, 'close_window'));
			} else if (hasStudents(frm)) {
				frm.add_custom_button(__('Open Window'), () => callWindowAction(frm, 'open_window'));
			}
		}
	},

	source_mode(frm) {
		toggleSourceFields(frm);
	},

	program_offering(frm) {
		frm.set_value('academic_year', null);
	},

	source_program_offering(frm) {
		frm.set_value('source_academic_year', null);
	},
});
