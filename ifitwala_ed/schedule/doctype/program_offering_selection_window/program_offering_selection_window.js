// Copyright (c) 2026, Francois de Ryckel and contributors
// For license information, please see license.txt

const VIEW_MODE_WINDOW_TRACKER = 'Selection Window Tracker';

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
	if ((method === 'load_students' || method === 'prepare_requests') && !hasSourceContext(frm)) {
		return;
	}
	frappe.call({
		doc: frm.doc,
		method,
		freeze: true,
		callback: () => frm.reload_doc(),
	});
}

function openRequestTracker(frm) {
	if (frm.is_new()) {
		frappe.msgprint(__('Please save this selection window first.'));
		return;
	}

	frappe.route_options = {
		view_mode: VIEW_MODE_WINDOW_TRACKER,
		selection_window: frm.doc.name,
		school: frm.doc.school || '',
		academic_year: frm.doc.academic_year || '',
		program: frm.doc.program || '',
		program_offering: frm.doc.program_offering || '',
		request_kind: 'Academic',
		latest_request_only: 1,
	};
	frappe.set_route('query-report', 'Program Enrollment Request Overview');
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
			frm.add_custom_button(__('View Request Tracker'), () => openRequestTracker(frm));
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

function hasSourceContext(frm) {
	const sourceMode = frm.doc.source_mode || 'Manual';

	if (sourceMode === 'Program Enrollment') {
		if (!frm.doc.source_program_offering || !frm.doc.source_academic_year) {
			frappe.msgprint(__('Choose Source Program Offering and Source Academic Year before loading students.'));
			return false;
		}
		return true;
	}

	if (sourceMode === 'Cohort') {
		if (!frm.doc.source_student_cohort) {
			frappe.msgprint(__('Choose Source Student Cohort before loading students.'));
			return false;
		}
		return true;
	}

	if (sourceMode === 'Manual' && !hasStudents(frm)) {
		frappe.msgprint(__('Add student rows manually, or choose Cohort or Program Enrollment as the source mode.'));
		return false;
	}

	return true;
}
