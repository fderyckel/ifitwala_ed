// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on('Program Enrollment Tool', {

	refresh: function(frm) {
		frm.disable_save();
		frm.fields_dict.enroll_students.$input.addClass(' btn btn-primary'); 

    frm.add_fetch('student', 'student_full_name', 'student_name');

		frappe.realtime.on("program_enrollment_tool", data => {
			frappe.hide_msgprint(true);
			frappe.show_progress(__("Enrolling students"), data.progress[0], data.progress[1]);
		});
	},

	// logic for the "get students" button.  Calling the get_students function in .py file.
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
				if(r.message) {
					frm.set_value("students", r.message);
				}
			}
		});
	},

	// logic for the "enroll student" button.
	enroll_students: function(frm) {
		frappe.call({
			doc:frm.doc,
			method: "enroll_students",
			callback: function(r) {
				frm.set_value("students", []);
			}
		});
	}
});
