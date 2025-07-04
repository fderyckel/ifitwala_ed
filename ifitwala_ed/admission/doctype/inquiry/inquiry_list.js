// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings['Inquiry'] = {
	get_indicator(doc) {
		if (doc.workflow_state === 'Assigned' && doc.first_contact_deadline) {
			const today = frappe.datetime.nowdate();  // JS-friendly string date (e.g., '2025-07-04')
			const days_diff = frappe.datetime.get_diff(doc.first_contact_deadline, today);

			if (days_diff < 0) {
				// Overdue
				return [__('🔴 Overdue'), 'red', 'workflow_state,=,Assigned'];
			}
			if (days_diff === 0) {
				// Due today
				return [__('🟡 Due Today'), 'orange', 'workflow_state,=,Assigned'];
			}
			// Optional: Upcoming indicator
			if (days_diff > 0) {
				return [__('⚪ Upcoming'), 'blue', 'workflow_state,=,Assigned'];
			}
		}
	}
};
