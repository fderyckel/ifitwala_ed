// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings['Inquiry'] = {
	// ensure these fields are loaded into the list view
	add_fields: ["sla_status", "workflow_state", "first_contact_due_on", "followup_due_on"],
	filters: [["workflow_state", "!=", "Archived"]],

	// formatters allow us to colour individual columns
	formatters: {
		// colour the SLA status column
		sla_status: function (value) {
			const colourMap = {
				'🔴 Overdue': 'red',
				'🟡 Due Today': 'orange',
				'⚪ Upcoming': 'blue',
				'✅ On Track': 'green'
			};
			const colour = colourMap[value] || 'gray';
			return `<span class="indicator-pill ${colour}">${value}</span>`;
		},
		first_contact_due_on: function (value) {
			const rawValue = String(value || '').trim();
			if (!rawValue) {
				return '<span class="text-muted">—</span>';
			}

			const today = frappe.datetime.get_today();
			const display = frappe.datetime.str_to_user(rawValue);

			let colour = 'blue';
			if (rawValue < today) {
				colour = 'red';
			} else if (rawValue === today) {
				colour = 'orange';
			}

			return `<span class="indicator-pill ${colour}">${frappe.utils.escape_html(display)}</span>`;
		},

		// colour the workflow_state column
		workflow_state: function (value) {
			const rawValue = String(value || '').trim();
			const colourMap = {
				'New': 'gray',
				'Assigned': 'blue',
				'Contacted': 'green',
				'Qualified': 'purple',
				'Archived': 'gray'
			};
			const colour = colourMap[rawValue];
			if (!colour) {
				console.error(`Unknown Inquiry workflow_state: ${rawValue}`);
				return `<span class="indicator-pill gray">${frappe.utils.escape_html(rawValue || __('Unknown'))}</span>`;
			}
			return `<span class="indicator-pill ${colour}">${frappe.utils.escape_html(rawValue)}</span>`;
		}
	}
};
