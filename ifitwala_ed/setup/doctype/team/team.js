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
					role_options = df.options.split('\n').filter(Boolean);
				} else {
					role_options = ['Member', 'Facilitator', 'Coordinator', 'Observer', 'Custom'];
				}
				if (!role_options.length) {
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
					const existingMembers = new Set(
						(frm.doc.members || [])
							.map(row => row.member)
							.filter(Boolean)
					);
					const users = (r.message || []).filter(u => u.value && !existingMembers.has(u.value));
					if (!users.length) {
						frappe.msgprint(__('All eligible users are already part of this team.'));
						return;
					}

					const d = new frappe.ui.Dialog({
						title: __('Invite Team Members'),
						size: 'large',
						fields: [
							{
								fieldname: 'search',
								fieldtype: 'Data',
								label: __('Search people...')
							},
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

					const ensure_dialog_style = () => {
						if (document.getElementById('team-member-dialog-style')) return;
						const style = document.createElement('style');
						style.id = 'team-member-dialog-style';
						style.textContent = `
							.team-member-dialog {
								padding-bottom: 0.5rem;
							}
							.team-member-dialog__intro h5 {
								font-weight: 600;
								color: #0f172a;
								margin-bottom: 0.25rem;
							}
							.team-member-dialog__intro p {
								margin: 0;
								color: #475569;
							}
							.team-member-card {
								border: 1px solid #e2e8f0;
								border-radius: 12px;
								padding: 0.85rem 1rem;
								margin-bottom: 0.75rem;
								background: #fff;
								box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
							}
							.team-member-card:hover {
								border-color: #cbd5f5;
								box-shadow: 0 4px 12px rgba(37, 99, 235, 0.12);
							}
							.team-member-name {
								font-weight: 600;
								color: #0f172a;
								display: block;
							}
							.team-member-id {
								font-size: 0.85rem;
								color: #64748b;
							}
							.team-member-role {
								min-width: 160px;
								border-radius: 999px;
								background: #f8fafc;
							}
							.team-member-empty {
								padding: 2.5rem 0;
								color: #94a3b8;
							}
						`;
						document.head.appendChild(style);
					};

					const options_html = role_options
						.map(opt => {
							const esc_opt = frappe.utils.escape_html(opt);
							const selected = esc_opt === default_role ? 'selected' : '';
							return `<option value="${esc_opt}" ${selected}>${esc_opt}</option>`;
						})
						.join('');

					const cards = users
						.map(u => {
							const label = frappe.utils.escape_html(u.label);
							const value = frappe.utils.escape_html(u.value);
							const searchValue = `${(u.label || '').toLowerCase()} ${(u.value || '').toLowerCase()}`;
							return `
								<div class="team-member-card d-flex flex-column flex-md-row align-items-md-center gap-3"
									data-search="${frappe.utils.escape_html(searchValue)}">
									<label class="d-flex align-items-start gap-3 flex-grow-1 mb-0">
										<input type="checkbox"
											class="team-member-checkbox mt-1"
											data-user="${value}"
											data-label="${label}">
										<div>
											<span class="team-member-name">${label}</span>
											<span class="team-member-id">${value}</span>
										</div>
									</label>
									<div class="ms-auto w-100 w-md-auto">
										<label class="text-muted small d-block mb-1">${__('Role in Team')}</label>
										<select class="team-member-role form-select" data-user="${value}">
											${options_html}
										</select>
									</div>
								</div>
							`;
						})
						.join('');

					ensure_dialog_style();

					const body_html = `
						<div class="team-member-dialog__intro mb-3">
							<h5>${__('Grow the team')}</h5>
							<p>${__('Choose a few colleagues and give them the right hat before adding them to the roster.')}</p>
						</div>
						<div class="team-member-grid">
							${cards}
						</div>
						<div class="team-member-empty text-center d-none">
							${__('No matches found. Try another search.')}
						</div>
					`;

					const $dialogBody = d.fields_dict.members_html.$wrapper
						.addClass('team-member-dialog')
						.html(body_html);

					const $grid = $dialogBody.find('.team-member-grid');
					const $emptyState = $dialogBody.find('.team-member-empty');

					const apply_search = term => {
						const normalized = (term || '').toLowerCase();
						let visible = 0;
						$grid.find('.team-member-card').each((_, el) => {
							const text = (el.getAttribute('data-search') || '').toLowerCase();
							const show = !normalized || text.includes(normalized);
							el.style.display = show ? '' : 'none';
							if (show) visible++;
						});
						if (visible) {
							$emptyState.addClass('d-none');
						} else {
							$emptyState.removeClass('d-none');
						}
					};

					apply_search('');

					const search_field = d.get_field('search');
					if (search_field && search_field.$input) {
						search_field.$input.on('input', () => {
							const term = search_field.$input.val();
							apply_search(term);
						});
					}

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
