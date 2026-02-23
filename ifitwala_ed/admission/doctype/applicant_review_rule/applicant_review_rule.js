// ifitwala_ed/admission/doctype/applicant_review_rule/applicant_review_rule.js

frappe.ui.form.on('Applicant Review Rule', {
	refresh(frm) {
		frm.set_query('school', () => {
			if (!frm.doc.organization) {
				return { filters: { name: '' } };
			}
			return {
				filters: {
					organization: frm.doc.organization,
				},
			};
		});

		frm.set_query('program_offering', () => {
			if (!frm.doc.school) {
				return { filters: { name: '' } };
			}
			return {
				filters: {
					school: frm.doc.school,
				},
			};
		});
	},
});
