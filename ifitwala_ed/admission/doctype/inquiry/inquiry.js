// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt


frappe.ui.form.on("Inquiry", {
	refresh(frm) {
		frm.page.clear_actions_menu();
		const s = frm.doc.workflow_state;
		const is_manager = frappe.user.has_role('Admission Manager');
		const is_officer = frappe.user.has_role('Admission Officer');

		if (s === 'New Inquiry' && is_manager) {
			frm.add_custom_button('Assign', () => frm.trigger('assign'));
		}
		if (s === 'Assigned' && is_officer) {
			frm.add_custom_button('Mark Contacted', () => frm.trigger('mark_contacted'));
		}
		if (s === 'Contacted' && is_officer) {
			frm.add_custom_button('Qualify', () => frm.trigger('qualify'));
		}
		if (frm.doctype === 'General Inquiry' && s === 'Qualified') {
			frm.add_custom_button('Start Nurturing', () => frm.trigger('start_nurturing'));
		}
		if (frm.doctype === 'Registration of Interest' && s === 'Qualified') {
			frm.add_custom_button('Submit Application', () => frm.trigger('submit_application'));
		}
		if (['Nurturing', 'Application Submitted'].includes(s) && is_manager) {
			frm.add_custom_button('Accept', () => frm.trigger('accept'));
			frm.add_custom_button('Disqualify', () => frm.trigger('disqualify'));
		}
	},

	assign(frm) {
		frappe.prompt(
			[
				{
					label: 'Assign To (Admission Officer)',
					fieldname: 'assigned_to',
					fieldtype: 'Link',
					options: 'User',
					reqd: 1,
					get_query: () => ({
						filters: {
							enabled: 1,
							'roles.role': 'Admission Officer'
						}
					})
				}
			],
			(values) => {
				frappe.call({
					method: 'ifitwala_ed.admission.utils.assign_inquiry',
					args: {
						doctype: frm.doctype,
						docname: frm.docname,
						assigned_to: values.assigned_to
					},
					callback: (r) => {
						if (!r.exc) {
							frappe.msgprint(__('Inquiry assigned to {0}', [values.assigned_to]));
							frm.reload_doc();
						}
					}
				});
			},
			__('Assign Inquiry'),
			__('Assign')
		);
	},

	mark_contacted(frm) {
		frm.set_value('workflow_state', 'Contacted');
		frm.save();
	},

	qualify(frm) {
		frm.set_value('workflow_state', 'Qualified');
		frm.save();
	},

	start_nurturing(frm) {
		frm.set_value('workflow_state', 'Nurturing');
		frm.save();
	},

	submit_application(frm) {
		frm.set_value('workflow_state', 'Application Submitted');
		frm.save();
	},

	accept(frm) {
		frm.set_value('workflow_state', 'Accepted / Enrolled');
		frm.save();
	},

	disqualify(frm) {
		frm.set_value('workflow_state', 'Unqualified / Lost');
		frm.save();
	}
});
