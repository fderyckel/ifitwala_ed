// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Inquiry", {
	refresh(frm) {
		frm.page.clear_actions_menu();
		const s = frm.doc.workflow_state;

		if (s==='New Inquiry' && frappe.user.has_role('Admission Manager')) {
			frm.add_custom_button('Assign', () => frm.trigger('assign'));
		}
		if (s==='Assigned' && frappe.user.has_role('Admission Officer')) {
			frm.add_custom_button('Mark Contacted', () => frm.trigger('mark_contacted'));
		}
		if (s==='Contacted' && frappe.user.has_role('Admission Officer')) {
			frm.add_custom_button('Qualify', () => frm.trigger('qualify'));
		}

		if (frm.doctype==='General Inquiry' && s==='Qualified') {
			frm.add_custom_button('Start Nurturing', () => frm.trigger('start_nurturing'));
		}
		if (frm.doctype==='Registration of Interest' && s==='Qualified') {
			frm.add_custom_button('Submit Application', () => frm.trigger('submit_application'));
		}

		if (['Nurturing','Application Submitted'].includes(s)
			&& frappe.user.has_role('Admission Manager')) {
			frm.add_custom_button('Accept', () => frm.trigger('accept'));
			frm.add_custom_button('Disqualify', () => frm.trigger('disqualify'));
		}
	},

	assign(frm) { /* open user-select dialog → set assigned_to + workflow_state='Assigned' */ },
	mark_contacted(frm) { frm.set_value('workflow_state','Contacted'); frm.save(); },
	qualify(frm) { frm.set_value('workflow_state','Qualified'); frm.save(); },
	start_nurturing(frm) { frm.set_value('workflow_state','Nurturing'); frm.save(); },
	submit_application(frm) { frm.set_value('workflow_state','Application Submitted'); frm.save(); },
	accept(frm) { frm.set_value('workflow_state','Accepted / Enrolled'); frm.save(); },
	disqualify(frm) { frm.set_value('workflow_state','Unqualified / Lost'); frm.save(); },
});
