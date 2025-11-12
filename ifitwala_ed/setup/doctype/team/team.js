// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed.setup.doctype.team.team.team.js

frappe.ui.form.on('Team', {
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Add Members'), () => {
				// Get dynamic roles from the child doctype
				const df = frappe.meta.get_docfield('Team Member', 'role_in_team', frm.doc.name);
				let role_options = [];
				if (df && df.options) {
					role_options = df.options.split('\n');
				} else {
					role_options = ['Member', 'Facilitator', 'Coordinator', 'Observer', 'Custom'];
				}

				// Fetch eligible users by school/org hierarchy
				frappe.call({
					method: 'ifitwala_ed.setup.doctype.team.team.get_eligible_users',
					args: {
						school: frm.doc.school,
						organization: frm.doc.organization
					}
				}).then(r => {
					const users = r.message || [];
					if (!users.length) {
						frappe.msgprint(__('No eligible users found for the selected School and Organization.'));
						return;
					}

					const options = users.map(u => `${u.value}:${u.label}`).join('\n');

					const d = new frappe.ui.Dialog({
						title: __('Select Members'),
						fields: [
							{
								fieldname: 'users',
								fieldtype: 'MultiSelect',
								label: __('Users'),
								options: options
							},
							{
								fieldname: 'role',
								fieldtype: 'Select',
								label: __('Role in Team'),
								options: role_options.join('\n'),
								default: role_options.includes('Member') ? 'Member' : role_options[0]
							}
						],
						primary_action_label: __('Add'),
						primary_action: data => {
							const user_list = (data.users || '').split('\n').filter(Boolean);
							if (!user_list.length) {
								frappe.msgprint(__('Please select at least one user.'));
								return;
							}
							user_list.forEach(u_val => {
								const user = u_val.split(':')[0];
								frm.add_child('members', {
									member: user,
									role_in_team: data.role,
									active: 1
								});
							});
							frm.refresh_field('members');
							d.hide();
							frappe.show_alert({
								message: __('Added {0} new member(s)', [user_list.length]),
								indicator: 'green'
							});
						}
					});
					d.show();
				});
			});
		}

		// Filter member Link field by school & organization hierarchy
		const member_field = frm.fields_dict.members?.grid.get_field('member');
		if (member_field) {
			member_field.get_query = function () {
				return {
					filters: {
						employee_school: frm.doc.school || '',
						employee_organization: frm.doc.organization || ''
					}
				};
			};
		}
	}
});

frappe.ui.form.on('Team Member', {
	member(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.member) {
			frappe.db.get_value('User', row.member, 'full_name')
				.then(res => {
					frappe.model.set_value(cdt, cdn, 'member_name', res.message.full_name);
				});
		}
	}
});



