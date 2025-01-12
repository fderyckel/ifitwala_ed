// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on('Student Patient Visit', {
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
		frappe.call({
			method: 'ifitwala_ed.health.doctype.student_patient.student_patient.get_student_detail',
			args: {
				student_patient: frm.doc.student_patient
			},
			callback: function(data) {
				let age = '';
				if (data.message.date_of_birth) {
					age = calculate_age(data.message.date_of_birth);
				}
				let values = {
					'student_age': age,
					'student_name':data.message.student_name,
					'gender': data.message.gender,
					'blood_group': data.message.blood_group
				};
				frm.set_value(values);
			}
		});
	}
});

let calculate_age = function(birth) {
	let ageMS = Date.parse(Date()) - Date.parse(birth);
	let age = new Date();
	age.setTime(ageMS);
	let years =  age.getFullYear() - 1970;
	return  years + ' Year(s) ' + age.getMonth() + ' Month(s) ' + age.getDate() + ' Day(s)';
};
