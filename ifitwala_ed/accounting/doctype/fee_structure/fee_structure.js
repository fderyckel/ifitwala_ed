// Copyright (c) 2021, ifitwala and contributors
// For license information, please see license.txt

frappe.provide('ifitwala_ed.accounting.dimensions');

frappe.ui.form.on('Fee Structure', {
	setup: function(frm) {
		frm.add_fetch('Organization', 'default_receivable_account', 'receivable_account');
		frm.add_fetch('Organization', 'default_income_account', 'income_account');
		frm.add_fetch('Organization', 'default_cost_center', 'cost_center');
	},

	organization: function(frm) {
		ifitwala_ed.accounting.dimensions.update_dimension(frm, frm.doctype);
	},

	onload: function(frm) {
		frm.set_query('academic_term', function() {
			return {
				filters: {'academic_year': frm.doc.academic_year}
			};
		});

		frm.set_query('receivable_account', function() {
			return {
				filters: {
					'account_type': 'Receivable',
					'is_group': 0,
					'organization': frm.doc.organization
				}
			};
		});

		frm.set_query('income_account', function() {
			return {
				filters: {
					'account_type': 'Income Account',
					'is_group': 0,
					'organization': frm.doc.organization
				}
			};
		});

		ifitwala_ed.accounting.dimensions.setup_dimension_filters(frm, frm.doctype)
	},

	refresh: function(frm) {
		if (frm.doc.status === 1) {
			frm.add_custom_button(__('Create Fee Schedule'), function() {
				frm.events.make_fee_schedule(frm);
			})addClass('btn-primary');
		}
	},

	make_fee_schedule: function(frm) {
		frappe.model.open_mapped_doc({
			method: ifitwala_ed.accounting.doctype.fee_structure.fee_structure.make_fee_schedule,
			frm: frm
		});
	}
});

frappe.ui.form.on('Fee Component', {
	amount: function(frm) {
		var total_amount = 0;
		for (var i=0;i<frm.doc.components.length;i++) {
			total_amount += frm.doc.components[i].amount;
		}
		frm.set_value('total_amount', total_amount);
	}
});
