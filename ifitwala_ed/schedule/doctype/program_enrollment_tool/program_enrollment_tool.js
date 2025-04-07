// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on('Program Enrollment Tool', {
	
	refresh: function(frm) {
		frm.disable_save();
		frm.fields_dict.enroll_students.$input.addClass('btn btn-primary');
		frm.add_fetch('student', 'student_full_name', 'student_name');

		// Setup dynamic field toggle
		toggle_filter_fields(frm);

		frappe.realtime.on("program_enrollment_tool", data => {
			frappe.hide_msgprint(true);
			frappe.show_progress(__("Enrolling students"), data.progress[0], data.progress[1]);
		});
	},

	get_students_from: function(frm) {
		toggle_filter_fields(frm);
	},

	program: function(frm) {
		frm.set_value("academic_year", null);

		if (frm.doc.program) {
			frappe.db.get_value("Program", frm.doc.program, "school")
				.then(({ message }) => {
					if (message && message.school) {
						frm.set_query("academic_year", function () {
							return {
								query: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_academic_years",
								filters: {
									school: message.school
								}
							};
						});
					}
				});
		}
	},

	new_program: function(frm) {
		frm.set_value("new_academic_year", null);

		if (frm.doc.new_program) {
			frappe.db.get_value("Program", frm.doc.new_program, "school")
				.then(({ message }) => {
					if (message && message.school) {
						frm.set_query("new_academic_year", function () {
							return {
								query: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_academic_years",
								filters: {
									school: message.school
								}
							};
						});
					}
				});
		}
	},

	get_students: function(frm) {
		if (!frm.doc.get_students_from) {
			frappe.msgprint(__('Please select "Get Students From" before fetching students.'));
			return;
		}

		if (frm.doc.get_students_from === "Program Enrollment") {
			if (!frm.doc.academic_year || !frm.doc.program) {
				frappe.msgprint(__('Please select both Academic Year and Program.'));
				return;
			}
		}

		if (frm.doc.get_students_from === "Cohort" && !frm.doc.student_cohort) {
			frappe.msgprint(__('Please select a Student Cohort.'));
			return;
		}

		frm.set_value("students", []);
		frappe.call({
			doc: frm.doc,
			method: "get_students",
			callback: function(r) {
				if (r.message) {
					frm.set_value("students", r.message);
				}
			}
		});
	},

	enroll_students: function(frm) {
		frappe.call({
			doc: frm.doc,
			method: "enroll_students",
			callback: function() {
				frm.set_value("students", []);
			}
		});
	}
});

function toggle_filter_fields(frm) {
	const source = frm.doc.get_students_from;

	frm.toggle_display('program', false);
	frm.toggle_display('academic_year', false);
	frm.toggle_display('student_cohort', false);

	if (source === "Program Enrollment") {
		frm.toggle_display('program', true);
		frm.toggle_display('academic_year', true);
		frm.toggle_display('student_cohort', true); // optional
	}
	else if (source === "Cohort") {
		frm.toggle_display('student_cohort', true);
	}
}
