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
		// Allow reassign if already assigned
		if (s === 'Assigned' && is_manager) {
			frm.add_custom_button('Reassign', () => frm.trigger('reassign'));
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
		if (!frm.doc.contact && frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Create Contact'), () => {
				frappe.call({
					doc: frm.doc,
					method: 'create_contact_from_inquiry',
					callback: (r) => {
						if (!r.exc) {
							frappe.show_alert({
								message: __('Contact Created: {0}', [r.message]),
								indicator: 'green'
							});
							frm.reload_doc();
						}
					}
				});
			});
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
						query: "ifitwala_ed.admission.admission_utils.get_admission_officers"
					})
				}
			],
			(values) => {
				frappe.call({
					method: 'ifitwala_ed.admission.admission_utils.assign_inquiry',
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

	reassign(frm) {
		frappe.prompt( 
			[
				{
					label: 'Reassign To (Admission Officer)',
					fieldname: 'new_assigned_to',
					fieldtype: 'Link',
					options: 'User',
					reqd: 1,
					get_query: () => ({
						query: 'ifitwala_ed.admission.admission_utils.get_admission_officers'
					})
				}
			],
			(values) => {
				frappe.call({
					method: 'ifitwala_ed.admission.admission_utils.reassign_inquiry',
					args: {
						doctype: frm.doctype,
						docname: frm.docname,
						new_assigned_to: values.new_assigned_to
					},
					callback: (r) => {
						if (!r.exc) {
							frappe.msgprint(__('Inquiry reassigned to {0}', [values.new_assigned_to]));
							frm.reload_doc();
						}
					}
				});
			},
			__('Reassign Inquiry'),
			__('Reassign')
		);
	}, 

	mark_contacted(frm) {
		frm.set_value('workflow_state', 'Contacted');
		frm.save().then(() => {
			frappe.call('frappe.desk.form.utils.add_comment', {
				reference_doctype: frm.doctype,
				reference_name: frm.docname,
				content: `Inquiry marked as <b>Contacted</b> by <b>${frappe.session.user}</b> on ${frappe.datetime.str_to_user(frappe.datetime.now_datetime())}.`,
				comment_type: 'Comment'
			});
		});
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
