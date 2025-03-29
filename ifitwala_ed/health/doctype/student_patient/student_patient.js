// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on('Student Patient', {
	onload(frm) {
        render_student_info(frm);

	}, 
	
	refresh: function(frm) { 
        render_student_info(frm);
        calculateAge(frm);

        if (frm.doc.student) {
            frm.add_custom_button( __("Guardian Details"),
                function () {
                    frappe.call({
                        method: "ifitwala_ed.health.doctype.student_patient.student_patient.get_guardian_details", 
                        args: {student_name: frm.doc.student},
                        callback: function (r) {
                            if (r.message) {
                                let guardian_details = r.message;
                                let message = "";
                                for (let guardian of guardian_details) {
                                    message += `
                                        <div style="margin-bottom: 10px; padding: 10px; border: 1px solid #d1d8dd;">
                                            <b>Guardian Name:</b> ${guardian.guardian_name}<br>
                                            <b>Relation:</b> ${guardian.relation}<br>
                                            <b>Email:</b> ${guardian.email_address || 'N/A'}<br>
                                            <b>Mobile:</b> ${guardian.mobile_number || 'N/A'}
                                        </div>
                                    `;
                                }
    
                                // Display details in a dialog
                                frappe.msgprint({
                                    title: __("Guardian Details"),
                                    message: __(message),
                                    indicator: 'blue',
                                });
                            } else {
                                frappe.msgprint(
                                    __("No guardian details found for this student.")
                                );
                            }
                        },
                    });
                }
            );
        }
    },
  });


// function to render student information
  function render_student_info(frm) {
	if (!frm.doc.student) return;

	frappe.db.get_value('Student', frm.doc.student, [
		'student_full_name',
		'student_preferred_name',
		'student_gender',
		'student_date_of_birth',
		'student_image'
	]).then(r => {
		if (!r.message) return;

		const student = r.message;
		const html = `
			<div>
				<b>Name:</b> ${student.student_full_name || '—'}<br>
				<b>Preferred Name:</b> ${student.student_preferred_name || '—'}<br>
				<b>Gender:</b> ${student.student_gender || '—'}<br>
				<b>Date of Birth:</b> ${frappe.format(student.student_date_of_birth, { fieldtype: 'Date' })}<br>
				${student.student_image ? `<img src="${student.student_image}" style="margin-top:10px;max-width:150px;">` : ''}
			</div>
		`;
		frm.fields_dict.student_info.$wrapper.html(html);
	});
}

// function to calculate age of the student as patient
function calculateAge(frm) {
  if (frm.doc.date_of_birth) {
      const dob = moment(frm.doc.date_of_birth);
      const today = moment();
      const years = today.diff(dob, 'year');
      dob.add(years, 'years');
      const months = today.diff(dob, 'months');
      dob.add(months, 'months');
      const days = today.diff(dob, 'days');

      const ageString = `${years} Years, ${months} Months and ${days} Days`;
      frm.set_value('student_age', ageString);
  } else {
      frm.set_value('student_age', '');
  }
}