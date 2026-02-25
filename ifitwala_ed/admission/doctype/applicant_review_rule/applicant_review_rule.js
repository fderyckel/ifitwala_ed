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

		frm.set_query('reviewer_user', 'reviewers', (_doc, cdt, cdn) => {
			const row = locals[cdt]?.[cdn] || {};
			const role = (row.reviewer_role || '').trim();
			if (!role) {
				return { query: 'frappe.core.doctype.user.user.user_query' };
			}
			return {
				query: 'ifitwala_ed.api.users.get_users_with_role',
				filters: { role },
			};
		});
	},
});
