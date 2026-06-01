function can_update_account_name_number(frm) {
	return (
		frm.has_perm('write') &&
		frm.doc.parent_account &&
		frappe.user &&
		frappe.user.has_role &&
		['Accounts Manager', 'System Manager'].some(role => frappe.user.has_role(role))
	);
}

function escape_account_preview(value) {
	return frappe.utils.escape_html(String(value || ''));
}

frappe.ui.form.on('Account', {
	setup: function (frm) {
		frm.add_fetch('parent_account', 'report_type', 'report_type');
		frm.add_fetch('parent_account', 'root_type', 'root_type');
	},
	onload: function (frm) {
		frm.set_query('parent_account', function (doc) {
			return {
				filters: {
					is_group: 1,
					organization: doc.organization,
				},
			};
		});
	},
	refresh: function (frm) {
		frm.toggle_enable(['account_name', 'account_number'], frm.is_new());

		if (!frm.is_new() && can_update_account_name_number(frm)) {
			frm.set_intro(null);
			frm.add_custom_button(
				__('Update Account Name / Number'),
				function () {
					frm.trigger('update_account_name_number');
				},
				__('Actions')
			);
		} else if (!frm.is_new() && frm.doc.parent_account && frm.has_perm('write')) {
			frm.set_intro(
				__('Only Accounts Manager or System Manager can update account names or numbers.'),
				'blue'
			);
		} else if (!frm.is_new() && !frm.doc.parent_account) {
			frm.set_intro(
				__('Root accounts cannot be renamed. Rename a child account from Actions instead.'),
				'blue'
			);
		}
	},
	update_account_name_number: function (frm) {
		var d = new frappe.ui.Dialog({
			title: __('Update Account Name / Number'),
			fields: [
				{
					label: __('Account Name'),
					fieldname: 'account_name',
					fieldtype: 'Data',
					reqd: 1,
					default: frm.doc.account_name,
				},
				{
					label: __('Account Number'),
					fieldname: 'account_number',
					fieldtype: 'Data',
					default: frm.doc.account_number,
				},
				{
					fieldname: 'preview',
					fieldtype: 'HTML',
				},
				{
					label: __('Reason'),
					fieldname: 'reason',
					fieldtype: 'Small Text',
					reqd: 1,
				},
			],
			primary_action_label: __('Update'),
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
					method: 'ifitwala_ed.accounting.doctype.account.account.update_account_name_number',
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
							message: __('Account updated'),
							indicator: 'green',
						});

						if (r.message && r.message.name) {
							frappe.set_route('Form', 'Account', r.message.name);
						} else {
							frm.reload_doc();
						}
					},
				});
			},
		});
		d.show();

		var render_preview = function (docname, is_error) {
			var label = escape_account_preview(__('New Document Name'));
			var message = docname || __('Enter an account name to preview the new document name.');
			var escaped_message = escape_account_preview(message);
			var message_class = is_error ? 'text-danger' : docname ? 'text-dark' : 'text-muted';

			d.get_field('preview').$wrapper.html(
				`<div class="small text-muted" style="margin-bottom: 4px;">${label}</div>
				<div class="${message_class}" style="border: 1px solid var(--border-color); border-radius: 6px; padding: 8px 10px; background: var(--control-bg); word-break: break-word;">${escaped_message}</div>`
			);
		};

		var refresh_preview = frappe.utils.debounce(function () {
			var account_name = d.get_value('account_name');
			if (!String(account_name || '').trim()) {
				render_preview('');
				return;
			}

			frappe.call({
				method:
					'ifitwala_ed.accounting.doctype.account.account.get_account_name_number_update_preview',
				args: {
					name: frm.doc.name,
					account_name: account_name,
					account_number: d.get_value('account_number'),
				},
				callback: function (r) {
					if (r.exc) {
						render_preview(__('Unable to preview the new document name.'), true);
						return;
					}
					render_preview(r.message && r.message.name);
				},
			});
		}, 250);

		d.get_field('account_name').$input.on('input', refresh_preview);
		d.get_field('account_number').$input.on('input', refresh_preview);
		refresh_preview();
	},
});
