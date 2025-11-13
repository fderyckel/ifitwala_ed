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
				const default_role =
					(df && df.default) ||
					(role_options.includes('Member') ? 'Member' : role_options[0]);

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

					const d = new frappe.ui.Dialog({
						title: __('Select Members'),
						fields: [
							{
								fieldname: 'members_html',
								fieldtype: 'HTML'
							}
						],
						primary_action_label: __('Add'),
						primary_action: () => {
							const selected = d.$wrapper.find('.team-member-checkbox:checked');
							if (!selected.length) {
								frappe.msgprint(__('Please select at least one user.'));
								return;
							}

							selected.each((_idx, checkbox) => {
								const $checkbox = $(checkbox);
								const user = $checkbox.data('user');
								const label = $checkbox.data('label');
								const role =
									d.$wrapper
										.find(`.team-member-role[data-user="${user}"]`)
										.val() || default_role;

								frm.add_child('members', {
									member: user,
									member_name: label,
									role_in_team: role,
									active: 1
								});
							});
							frm.refresh_field('members');
							d.hide();
							frappe.show_alert({
								message: __('Added {0} new member(s)', [selected.length]),
								indicator: 'green'
							});
						}
					});

					const render_member_rows = () => {
						const rows = users.map(u => {
							const label = frappe.utils.escape_html(u.label);
							const value = frappe.utils.escape_html(u.value);
							const options_html = role_options
								.map(opt => {
									const esc_opt = frappe.utils.escape_html(opt);
									const selected = esc_opt === default_role ? 'selected' : '';
									return `<option value="${esc_opt}" ${selected}>${esc_opt}</option>`;
								})
								.join('');

							return `
								<div class="team-member-row">
									<label class="checkbox">
										<input type="checkbox"
											class="team-member-checkbox"
											data-user="${value}"
											data-label="${label}">
										<span>${label}</span>
									</label>
									<select class="team-member-role form-control" data-user="${value}">
										${options_html}
									</select>
								</div>
							`;
						});

						return `
							<div class="team-member-grid">
								${rows.join('')}
							</div>
						`;
					};

					d.fields_dict.members_html.$wrapper
						.addClass('team-member-dialog')
						.html(render_member_rows());

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


