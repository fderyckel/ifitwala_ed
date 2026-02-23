// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on('Student Patient', {
	onload(frm) {
        fetch_and_render_student_info(frm);

	},

	refresh: function(frm) {
        fetch_and_render_student_info(frm);


		if (frm.doc.student) {
            // logic for Guardian details button to display main info about the guardians
			frm.add_custom_button(__('Guardian Details'), function () {
				show_guardian_details_dialog(frm.doc.student);
			});

            // logic for the Student Visit button
	        frm.add_custom_button(__('Student Visit'), function () {
                frappe.new_doc('Student Patient Visit', {
                    student: frm.doc.student,
			        student_patient: frm.doc.name,
			        time_of_arrival: frappe.datetime.now_time()
		        });
	        });
		}
    }
  });

// function to render student info
function fetch_and_render_student_info(frm, student_fieldname = 'student') {
	const student_id = frm.doc[student_fieldname];
	if (!student_id) return;

	frappe.call({
		method: 'ifitwala_ed.health.doctype.student_patient.student_patient.get_student_basic_info',
		args: { student: student_id },
		callback: function (r) {
			if (!r.message) return;

			const s = r.message;

			// Calculate age and set it
			if (s.student_date_of_birth) {
				const age_string = calculate_age(s.student_date_of_birth);
				frm.set_value('student_age', age_string);
			} else {
				frm.set_value('student_age', '');
			}

			// Render info into HTML field
			const html = `
				<div>
					<b>Name:</b> ${s.student_full_name || '—'}<br>
					<b>Preferred Name:</b> ${s.student_preferred_name || '—'}<br>
					<b>Gender:</b> ${s.student_gender || '—'}<br>
					<b>Date of Birth:</b> ${frappe.format(s.student_date_of_birth, { fieldtype: 'Date' })}<br>
				</div>
			`;
			frm.fields_dict.student_info?.$wrapper.html(html);
		}
	});
}


// function to calculate age of the student as patient
function calculate_age(date_string) {
	const dob = moment(date_string);
	const today = moment();
	const years = today.diff(dob, 'years');
	dob.add(years, 'years');
	const months = today.diff(dob, 'months');
	dob.add(months, 'months');
	const days = today.diff(dob, 'days');
	return `${years} Year(s) ${months} Month(s) ${days} Day(s)`;
}


// function to show guardian details dialog (from the button)
function show_guardian_details_dialog(student_id) {
	frappe.call({
		method: 'ifitwala_ed.health.doctype.student_patient.student_patient.get_guardian_details',
		args: { student_name: student_id },
		callback: function (r) {
			if (r.message && r.message.length) {
				const message = r.message.map(guardian => `
					<div style="margin-bottom: 10px; padding: 10px; border: 1px solid #d1d8dd;">
						<b>Guardian Name:</b> ${guardian.guardian_name}<br>
						<b>Relation:</b> ${guardian.relation}<br>
						<b>Email:</b> ${guardian.email_address || 'N/A'}<br>
						<b>Mobile:</b> ${guardian.mobile_number || 'N/A'}
					</div>
				`).join('');

				frappe.msgprint({
					title: __('Guardian Details'),
					message: message,
					indicator: 'blue',
				});
			} else {
				frappe.msgprint(__('No guardian details found for this student.'));
			}
		}
	});
}
