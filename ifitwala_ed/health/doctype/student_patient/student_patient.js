// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on('Student Patient', {
	onload(frm) {
		cur_frm.add_fetch('student', 'student_gender', 'gender');
		cur_frm.add_fetch('student', 'student_date_of_birth', 'date_of_birth');
		cur_frm.add_fetch('student', 'student_preferred_name', 'preferred_name');
		cur_frm.add_fetch('student', 'student_full_name', 'student_name');

	}, 
	
	refresh: function(frm) { 
    calculateAge(frm);

    frappe.user.has_role("Nurse", () => {
      if (frm.doc.student) {
          frm.add_custom_button(
              __("Guardian Details"),
              function () {
                  frappe.call({
                      method: "ifitwala_ed.health.student_patient.get_guardian_details", 
                      args: {
                          student_name: frm.doc.student,
                      },
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
              },
              __("Actions")
          );
      }
  });
  },
});

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