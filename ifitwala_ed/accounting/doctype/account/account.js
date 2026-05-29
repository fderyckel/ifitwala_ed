frappe.ui.form.on("Account", {
	setup: function (frm) {
		frm.add_fetch("parent_account", "report_type", "report_type");
		frm.add_fetch("parent_account", "root_type", "root_type");
	},
	onload: function (frm) {
		frm.set_query("parent_account", function (doc) {
			return {
				filters: {
					is_group: 1,
					organization: doc.organization,
				},
			};
		});
	},
	refresh: function (frm) {
		frm.toggle_enable(["account_name", "account_number"], frm.is_new());

		if (!frm.is_new() && frm.has_perm("write") && frm.doc.parent_account) {
			frm.add_custom_button(
				__("Update Account Name / Number"),
				function () {
					frm.trigger("update_account_name_number");
				},
				__("Actions")
			);
		}
	},
	update_account_name_number: function (frm) {
		var d = new frappe.ui.Dialog({
			title: __("Update Account Name / Number"),
			fields: [
				{
					label: __("Account Name"),
					fieldname: "account_name",
					fieldtype: "Data",
					reqd: 1,
					default: frm.doc.account_name,
				},
				{
					label: __("Account Number"),
					fieldname: "account_number",
					fieldtype: "Data",
					default: frm.doc.account_number,
				},
				{
					label: __("Reason"),
					fieldname: "reason",
					fieldtype: "Small Text",
					reqd: 1,
				},
			],
			primary_action_label: __("Update"),
			primary_action: function () {
				var data = d.get_values();
				if (!data) {
					return;
				}
				if (
					data.account_number === frm.doc.account_number &&
					data.account_name === frm.doc.account_name
				) {
					d.hide();
					return;
				}

				frappe.call({
					method: "ifitwala_ed.accounting.doctype.account.account.update_account_name_number",
					args: {
						name: frm.doc.name,
						account_name: data.account_name,
						account_number: data.account_number,
						reason: data.reason,
					},
					callback: function (r) {
						if (r.exc) {
							return;
						}

						d.hide();
						frappe.show_alert({
							message: __("Account updated"),
							indicator: "green",
						});

						if (r.message && r.message.name) {
							frappe.set_route("Form", "Account", r.message.name);
						} else {
							frm.reload_doc();
						}
					},
				});
			},
		});
		d.show();
	},
});
