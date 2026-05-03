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

			frm.set_value('student_age', s.student_age || '');

			const dateOfBirthLine = s.student_date_of_birth
				? `<b>${__('Date of Birth')}:</b> ${frappe.format(s.student_date_of_birth, { fieldtype: 'Date' })}<br>`
				: '';

			// Render info into HTML field
			const html = `
				<div>
					<b>${__('Name')}:</b> ${s.student_full_name || __('—')}<br>
					<b>${__('Preferred Name')}:</b> ${s.student_preferred_name || __('—')}<br>
					<b>${__('Gender')}:</b> ${s.student_gender || __('—')}<br>
					<b>${__('Age')}:</b> ${s.student_age || __('—')}<br>
					${dateOfBirthLine}
				</div>
			`;
			frm.fields_dict.student_info?.$wrapper.html(html);
		}
	});
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
						<b>${__('Guardian Name')}:</b> ${guardian.guardian_name}<br>
						<b>${__('Relation')}:</b> ${guardian.relation}<br>
						<b>${__('Email')}:</b> ${guardian.email_address || __('N/A')}<br>
						<b>${__('Mobile')}:</b> ${guardian.mobile_number || __('N/A')}
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
