// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings['Inquiry'] = {
	// ensure these fields are loaded into the list view
	add_fields: ["sla_status", "workflow_state", "first_contact_due_on", "followup_due_on"],

	// primary row indicator: use the stored sla_status value
	get_indicator: function (doc) {
		// Map SLA status to colours
		const slaColourMap = {
			'🔴 Overdue': 'red',
			'🟡 Due Today': 'orange',
			'⚪ Upcoming': 'blue',
			'✅ On Track': 'green'
		};
		const label = doc.sla_status || __('⚪ Upcoming');
		const colour = slaColourMap[doc.sla_status] || 'blue';
		return [label, colour, ['sla_status','= ', label]];
	},

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

		// colour the workflow_state column
		workflow_state: function (value) {
			const colourMap = {
				'New': 'gray',
				'New Inquiry': 'gray',
				'Assigned': 'blue',
				'Contacted': 'green',
				'Qualified': 'purple',
				'Archived': 'gray',
				'Nurturing': 'orange',
				'Accepted': 'green',
				'Unqualified': 'red'
			};
			const colour = colourMap[value] || 'gray';
			return `<span class="indicator-pill ${colour}">${__(value)}</span>`;
		}
	}
};
