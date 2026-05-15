// ifitwala_ed/admission/doctype/applicant_review_rule_reviewer/applicant_review_rule_reviewer.js

frappe.ui.form.on('Applicant Review Rule Reviewer', {
	reviewer_mode(_frm, cdt, cdn) {
		const row = locals[cdt]?.[cdn];
		if (!row) return;

		const mode = (row.reviewer_mode || '').trim() || 'Role Only';
		if (mode === 'Role Only' && row.reviewer_user) {
			frappe.model.set_value(cdt, cdn, 'reviewer_user', null);
		}
	},

	reviewer_user(_frm, cdt, cdn) {
		const row = locals[cdt]?.[cdn];
		if (!row) return;

		const mode = (row.reviewer_mode || '').trim() || 'Role Only';
		if (mode === 'Role Only' && row.reviewer_user) {
			frappe.show_alert({
				message: __('Reviewer User is only allowed for Specific User mode.'),
				indicator: 'orange',
			});
			frappe.model.set_value(cdt, cdn, 'reviewer_user', null);
		}
	},
});
