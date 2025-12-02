// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on('Student Patient Visit', {
	// to ensure that when we opening the form using the frappe.new_doc(), the getting info is still triggered.
	onload(frm) {
		if (frm.doc.student_patient) {
			frm.events.set_student_info(frm);
		}

		if (!frm.doc.time_of_arrival) {
			frm.set_value('time_of_arrival', frappe.datetime.now_time());
		}
	},

	refresh: function(frm) { 
		
		frm.set_query('student_patient', function() {
			return {
				filters: {'status': 'Active'}
			};
		}); 
		
		// Set Time of Arrival on document load if not already set
		if (!frm.doc.time_of_arrival && !frm.doc.__islocal) {
			frm.set_value('time_of_arrival', frappe.datetime.now_time());
		}

	}, 
	
	// to show a non-clickable message to inform that a student log has been created
	after_save: function (frm) {
		if (frm.doc.docstatus === 1) {
			frappe.show_alert({
				message: '✅ Student Log has been created for this visit.',
				indicator: 'green'
			});
		}
	}, 

	before_submit: function(frm) {
		// Set Time of Discharge on before_submit if not already set
		if (!frm.doc.time_of_discharge) {
				frm.set_value('time_of_discharge', frappe.datetime.now_time());
		}
	}, 

	student_patient: function(frm) { 
		frm.events.set_student_info(frm);
	}, 
	
	set_student_info: function(frm) {
		// Step 1: Get the Student linked to this Student Patient
		if (!frm.doc.student_patient) return;
	
		frappe.db.get_value('Student Patient', frm.doc.student_patient, 'student')
			.then(r => {
				const student_id = r.message?.student;
				if (!student_id) return;
	
				// Step 2: Fetch student bio info from utility method
				frappe.call({
					method: 'ifitwala_ed.health.doctype.student_patient.student_patient.get_student_basic_info',
					args: { student: student_id },
					callback: function(res) {
						if (!res.message) return;
	
						const student = res.message;
						const age = student.student_date_of_birth
							? calculate_age(student.student_date_of_birth)
							: '';
	
						frm.set_value({
							student: student_id,
							student_name: student.student_full_name,
							gender: student.student_gender,
							date_of_birth: student.student_date_of_birth,
							student_age: age
						});
					}
				});

				// Step 3: Fetch School based on enrollment
				if (frm.doc.date) {
					frappe.call({
						method: 'ifitwala_ed.health.doctype.student_patient_visit.student_patient_visit.get_student_school',
						args: {
							student_patient: frm.doc.student_patient,
							date: frm.doc.date
						},
						callback: function(r) {
							if (r.message) {
								frm.set_value('school', r.message);
							}
						}
					});
				}
			});
	},

	date: function(frm) {
		if (frm.doc.student_patient) {
			frm.events.set_student_info(frm);
		}
	}
});

let calculate_age = function(birth) {
	let ageMS = Date.parse(Date()) - Date.parse(birth);
	let age = new Date();
	age.setTime(ageMS);
	let years =  age.getFullYear() - 1970;
	return  years + ' Year(s) ' + age.getMonth() + ' Month(s) ' + age.getDate() + ' Day(s)';
};
