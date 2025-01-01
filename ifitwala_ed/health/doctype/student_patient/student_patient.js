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
	}
		
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