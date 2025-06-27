// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings['Inquiry'] = {
	get_indicator(doc) {
		if (doc.workflow_state === 'Assigned' && doc.first_contact_deadline) {
			const days_diff = frappe.utils.date_diff(
				doc.first_contact_deadline,
				frappe.datetime.now_date()
			);
			if (days_diff < 0) {
				// Overdue
				return [__('Overdue'), 'red', 'workflow_state,=,Assigned'];
			}
			if (days_diff === 0) {
				// Due today
				return [__('Due Today'), 'yellow', 'workflow_state,=,Assigned'];
			}
		}
	}
};
