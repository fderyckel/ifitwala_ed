frappe.ui.form.on('Org Settings', {
	refresh: function(frm) {
		frm.trigger('setup_account_filters');
	},
	
	default_organization: function(frm) {
		frm.trigger('setup_account_filters');
	},

	setup_account_filters: function(frm) {
		let org = frm.doc.default_organization;
		
		let common_filters = {
			"is_group": 0,
			"disabled": 0
		};
		
		if (org) {
			common_filters["organization"] = org;
		}

		// Helper to apply filters
		let set_filter = (fieldname, extra_filters) => {
			frm.set_query(fieldname, () => {
				return {
					filters: { ...common_filters, ...extra_filters }
				};
			});
		};

		set_filter("default_accounts_receivable", { "account_type": "Receivable" });
		set_filter("default_cash_account", { "account_type": "Cash" });
		set_filter("default_bank_account", { "account_type": "Bank" });
		set_filter("default_advances_liability_account", { "root_type": "Liability" }); // Type blank or just Liability root
		set_filter("default_tax_payable_account", { "account_type": "Tax", "root_type": "Liability" });
	}
});
