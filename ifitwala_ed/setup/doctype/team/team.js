// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed.setup.doctype.team.team.team.js

frappe.ui.form.on('Team', {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__('Schedule Meetings'), () => {
				open_team_schedule_dialog(frm);
			});
		}

		frm.add_custom_button(__('Meeting Book'), () => {
			open_meeting_book_dialog(frm);
		}).addClass('btn-primary');


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
							.map(row => row.employee || row.member)
							.filter(Boolean)
					);
					const users = (r.message || []).filter(u => {
						const key = u.employee || u.value;
						return key && !existingMembers.has(key);
					});
					if (!users.length) {
						frappe.msgprint(__('All eligible employees are already part of this team.'));
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
								frappe.msgprint(__('Please select at least one employee.'));
								return;
							}

							let addedCount = 0;
							selected.each((_idx, checkbox) => {
								const $checkbox = $(checkbox);
								const employee = $checkbox.data('employee');
								const user = $checkbox.data('user');
								const label = $checkbox.data('label');
								const key = $checkbox.data('key');
								if (!employee) {
									return;
								}

								const role =
									d.$wrapper
										.find(`.team-member-role[data-key="${key}"]`)
										.val() || default_role;

								frm.add_child('members', {
									employee,
									member: user || null,
									member_name: label,
									role_in_team: role,
								});
								addedCount++;
							});
							if (!addedCount) {
								frappe.msgprint(__('No employees were added.'));
								return;
							}
							frm.refresh_field('members');
							d.hide();
							frappe.show_alert({
								message: __('Added {0} new member(s)', [addedCount]),
								indicator: 'green'
							});
						}
					});

					const ensure_dialog_style = () => {
						if (document.getElementById('team-member-dialog-style')) return;
						const style = document.createElement('style');
						style.id = 'team-member-dialog-style';
						style.textContent = `
							.team-member-grid {
								max-height: 24rem;
								overflow-y: auto;
								padding-right: 0.25rem;
							}
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
								padding: 1rem 1.1rem;
								margin-bottom: 0.75rem;
								background: #fff;
								box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
								display: flex;
								flex-wrap: wrap;
								gap: 1.5rem;
								align-items: center;
							}
							.team-member-card:hover {
								border-color: #cbd5f5;
								box-shadow: 0 4px 12px rgba(37, 99, 235, 0.12);
							}
							.team-member-card:focus {
								outline: none;
							}
							.team-member-card:focus-visible,
							.team-member-card:focus-within {
								border-color: #3b82f6;
								box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
							}
							.team-member-card__details {
								flex: 1;
								display: flex;
								align-items: flex-start;
								gap: 0.85rem;
								min-width: 260px;
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
								min-height: 44px;
								padding: 0.5rem 1.1rem;
							}
							.team-member-card__role {
								min-width: 230px;
								flex: 0 0 230px;
							}
							@media (max-width: 576px) {
								.team-member-card__role {
									flex: 1 1 100%;
								}
							}
							.team-member-checkbox {
								width: 1.25rem;
								height: 1.25rem;
								margin-top: 0.15rem;
							}
							.team-member-checkbox:focus-visible {
								outline: 2px solid #3b82f6;
								outline-offset: 2px;
							}
							.team-member-empty {
								padding: 2.5rem 0;
								color: #94a3b8;
							}
						`;
						document.head.appendChild(style);
					};

					const normalize_for_search = text => {
						const raw = (text || '').toString().toLowerCase();
						return raw.normalize ? raw.normalize('NFD').replace(/[\u0300-\u036f]/g, '') : raw;
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
							const employeeRaw = u.employee || '';
							const userRaw = u.value || '';
							const labelRaw = u.employee_name || u.label || '';
							const searchValue = normalize_for_search(
								[labelRaw, employeeRaw, userRaw].join(' ')
							);
							const label = frappe.utils.escape_html(labelRaw);
							const employeeId = frappe.utils.escape_html(employeeRaw);
							const userId = frappe.utils.escape_html(userRaw);
							const key = frappe.utils.escape_html(employeeRaw || userRaw);
							return `
								<div class="team-member-card" tabindex="0"
									data-search="${frappe.utils.escape_html(searchValue)}">
									<label class="team-member-card__details d-flex align-items-start gap-3 flex-grow-1 mb-0">
										<input type="checkbox"
											class="team-member-checkbox mt-1"
											data-key="${key}"
											data-employee="${employeeId}"
											data-user="${userId}"
											data-label="${label}">
										<div>
											<span class="team-member-name">${label}</span>
											${employeeId ? `<div class="team-member-id">${employeeId}</div>` : ''}
											${userId ? `<div class="team-member-id text-muted">${userId}</div>` : ''}
										</div>
									</label>
									<div class="team-member-card__role ms-auto w-100 w-md-auto">
										<label class="text-muted small d-block mb-1">${__('Role in Team')}</label>
										<select class="team-member-role form-select" data-key="${key}">
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

					const focus_card_at = index => {
						const $visible = $grid.find('.team-member-card:visible');
						if (!$visible.length) return;
						const targetIndex = Math.max(0, Math.min(index, $visible.length - 1));
						const $target = $visible.eq(targetIndex);
						if ($target.length) {
							$target.get(0).focus();
						}
						const container = $grid.get(0);
						if (container && $target.length) {
							const cardEl = $target.get(0);
							const { top, bottom } = cardEl.getBoundingClientRect();
							const parentRect = container.getBoundingClientRect();
							if (top < parentRect.top) {
								container.scrollTop -= parentRect.top - top + 8;
							} else if (bottom > parentRect.bottom) {
								container.scrollTop += bottom - parentRect.bottom + 8;
							}
						}
					};

					const apply_search = term => {
						const normalized = normalize_for_search(term || '');
						let visible = 0;
						$grid.find('.team-member-card').each((_, el) => {
							const text = el.getAttribute('data-search') || '';
							const show = !normalized || text.includes(normalized);
							el.style.display = show ? '' : 'none';
							if (show) visible++;
						});
						if (visible) {
							$emptyState.addClass('d-none');
						} else {
							$emptyState.removeClass('d-none');
						}
						const activeEl = document.activeElement;
						if (
							activeEl &&
							activeEl.classList.contains('team-member-card') &&
							activeEl.style.display === 'none'
						) {
							focus_card_at(0);
						}
					};

					apply_search('');

					const search_field = d.get_field('search');
					if (search_field && search_field.$input) {
						search_field.$input
							.attr('placeholder', __('Search people...'))
							.attr('aria-label', __('Search people'));
						search_field.$input.on('input', () => {
							const term = search_field.$input.val();
							apply_search(term);
						});
						search_field.$input.on('keydown', e => {
							if (e.key === 'ArrowDown') {
								e.preventDefault();
								focus_card_at(0);
							}
						});
					}

					$grid.on('keydown', '.team-member-card, .team-member-card *', e => {
						const $card = $(e.target).closest('.team-member-card');
						if (!$card.length) return;
						if (e.target !== $card.get(0)) {
							return;
						}
						if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
							e.preventDefault();
							const $visible = $grid.find('.team-member-card:visible');
							const currentIndex = $visible.index($card);
							if (currentIndex === -1) return;
							const delta = e.key === 'ArrowDown' ? 1 : -1;
							focus_card_at(currentIndex + delta);
							return;
						}
						if (
							(e.key === ' ' || e.key === 'Spacebar' || e.code === 'Space') &&
							e.target === $card.get(0)
						) {
							e.preventDefault();
							const $checkbox = $card.find('.team-member-checkbox').first();
							if ($checkbox.length) {
								$checkbox.prop('checked', !$checkbox.prop('checked'));
							}
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

		const employee_field = frm.fields_dict.members?.grid.get_field('employee');
		if (employee_field) {
			employee_field.get_query = function () {
				return {
					filters: {
						school: frm.doc.school || '',
						organization: frm.doc.organization || ''
					}
				};
			};
		}
	}
});

frappe.ui.form.on('Team Member', {
	employee(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.employee) {
			frappe.model.set_value(cdt, cdn, 'member', null);
			frappe.model.set_value(cdt, cdn, 'member_name', null);
			return;
		}

		frappe.db.get_value('Employee', row.employee, ['employee_full_name', 'user_id'])
			.then(res => {
				const data = res.message || {};
				if (data.employee_full_name) {
					frappe.model.set_value(cdt, cdn, 'member_name', data.employee_full_name);
				}
				if (data.user_id) {
					frappe.model.set_value(cdt, cdn, 'member', data.user_id);
				}
			});
	},
	member(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.member) {
			return;
		}

		frappe.db.get_value('User', row.member, 'full_name')
			.then(res => {
				const fullName = res.message?.full_name;
				if (fullName) {
					frappe.model.set_value(cdt, cdn, 'member_name', fullName);
				}
			});

		if (!row.employee) {
			frappe.db.get_value('Employee', { user_id: row.member }, 'name')
				.then(res => {
					const employee = res.message?.name;
					if (employee) {
						frappe.model.set_value(cdt, cdn, 'employee', employee);
					}
				});
		}
	}
});


function open_meeting_book_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __('Meeting Book'),
		fields: [
			{
				fieldname: 'academic_year',
				fieldtype: 'Link',
				label: __('Academic Year'),
				options: 'Academic Year',
				reqd: 0,
				description: __('Optional. Leave blank to include all non-cancelled meetings for this team.')
			},
			{
				fieldname: 'from_date',
				fieldtype: 'Date',
				label: __('From Date')
			},
			{
				fieldname: 'to_date',
				fieldtype: 'Date',
				label: __('To Date')
			}
		],
		primary_action_label: __('Open'),
		primary_action(values) {
			if (!frm.doc.name) {
				frappe.msgprint(__('Please save the team first.'));
				return;
			}

			// Basic sanity: if only one of from/to is set, allow it.
			// If both are set, ensure from <= to.
			if (values.from_date && values.to_date) {
				const from = frappe.datetime.str_to_obj(values.from_date);
				const to = frappe.datetime.str_to_obj(values.to_date);
				if (from > to) {
					frappe.msgprint(__('From Date must be on or before To Date.'));
					return;
				}
			}

			// Pre-open a blank window to avoid popup blockers
			const win = window.open('', '_blank');
			if (!win) {
				frappe.msgprint(__('Please allow pop-ups to view the meeting book.'));
				return;
			}

			win.document.write(`
				<!DOCTYPE html>
				<html>
					<head>
						<meta charset="utf-8">
						<title>${__('Meeting Book')} – ${frappe.utils.escape_html(frm.doc.team_name || frm.doc.name)}</title>
					</head>
					<body style="font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 24px;">
						<p>${__('Loading meeting book…')}</p>
					</body>
				</html>
			`);

			const params = {
				team: frm.doc.name
			};
			if (values.academic_year) {
				params.academic_year = values.academic_year;
			}
			if (values.from_date) {
				params.from_date = values.from_date;
			}
			if (values.to_date) {
				params.to_date = values.to_date;
			}

			frappe.call({
				method: 'ifitwala_ed.setup.doctype.meeting.meeting.get_team_meeting_book',
				args: params
			}).then(r => {
				const html = r.message || '<p>No content.</p>';
				win.document.open();
				win.document.write(html);
				win.document.close();
			}).catch(() => {
				win.document.open();
				win.document.write('<p style="color:#b91c1c;">Error while generating meeting book.</p>');
				win.document.close();
			});

			d.hide();
		}
	});

	// Optional: filter AY by team.school using your existing link query
	d.fields_dict.academic_year.get_query = () => ({
		query: 'ifitwala_ed.utilities.link_queries.academic_year_link_query',
		filters: {
			school: frm.doc.school
		}
	});

	d.show();
}

const TEAM_MEETING_MAX_OCCURRENCES = 40;
const TEAM_MEETING_RECURRENCE_OPTIONS = [
	{ value: 'weekly', label: __('Every week'), description: __('Great for standing huddles.') },
	{ value: 'biweekly', label: __('Every 2 weeks'), description: __('Keeps momentum without crowding the calendar.') },
	{ value: 'three_weeks', label: __('Every 3 weeks'), description: __('Perfect for checkpoint cadences.') },
	{ value: 'monthly', label: __('Every month'), description: __('Use for retros or planning reviews.') }
];
const TEAM_MEETING_RECURRENCE_META = {
	weekly: { unit: 'week', step: 1 },
	biweekly: { unit: 'week', step: 2 },
	three_weeks: { unit: 'week', step: 3 },
	monthly: { unit: 'month', step: 1 }
};
const dayjs =
	window.dayjs ||
	(frappe.datetime && frappe.datetime.moment ? frappe.datetime.moment : null) ||
	window.moment;

function open_team_schedule_dialog(frm) {
	const activeMembers = (frm.doc.members || []).filter(m => m.employee);
	if (!activeMembers.length) {
		frappe.msgprint({
			title: __('Add members'),
			message: __('Please add at least one employee before scheduling team meetings.'),
			indicator: 'orange'
		});
		return;
	}

	frappe.model.with_doctype('Meeting', () => {
		ensure_scheduler_styles();

		const meetingMeta = frappe.get_meta('Meeting');
		const meetingCategoryField = meetingMeta?.fields?.find(df => df.fieldname === 'meeting_category');
		const meetingCategoryOptions = (meetingCategoryField?.options || '').split('\n').filter(Boolean);
		const recurrenceLabels = TEAM_MEETING_RECURRENCE_OPTIONS.map(opt => opt.label);
		const recurrenceValueByLabel = Object.fromEntries(TEAM_MEETING_RECURRENCE_OPTIONS.map(opt => [opt.label, opt.value]));
		const recurrenceLabelByValue = Object.fromEntries(TEAM_MEETING_RECURRENCE_OPTIONS.map(opt => [opt.value, opt.label]));

		const dialog = new frappe.ui.Dialog({
			title: __('Schedule Meetings'),
			size: 'large',
			fields: [
				{ fieldname: 'intro_html', fieldtype: 'HTML' },
				{ fieldtype: 'Section Break', label: __('Academic Year') },
				{
					fieldname: 'academic_year',
					fieldtype: 'Link',
					label: __('Academic Year'),
					options: 'Academic Year',
					reqd: 1
				},
				{ fieldname: 'ay_window', fieldtype: 'HTML' },
				{ fieldtype: 'Section Break', label: __('Meeting Blueprint') },
				{
					fieldname: 'meeting_title',
					fieldtype: 'Data',
					label: __('Meeting Title'),
					reqd: 1
				},
				{
					fieldname: 'start_date',
					fieldtype: 'Date',
					label: __('Start Date'),
					reqd: 1
				},
				{
					fieldname: 'start_time',
					fieldtype: 'Time',
					label: __('Start Time'),
					reqd: 1
				},
				{
					fieldname: 'end_time',
					fieldtype: 'Time',
					label: __('End Time'),
					reqd: 1
				},
				{ fieldname: 'column_break_schedule', fieldtype: 'Column Break' },
				{
					fieldname: 'location',
					fieldtype: 'Link',
					label: __('Location'),
					options: 'Location'
				},
				{
					fieldname: 'virtual_meeting_link',
					fieldtype: 'Data',
					label: __('Virtual Meeting Link'),
					options: 'URL'
				},
				{
					fieldname: 'meeting_category',
					fieldtype: 'Select',
					label: __('Meeting Category')
				},
				{ fieldtype: 'Section Break', label: __('Recurrence') },
				{
					fieldname: 'repeat_option',
					fieldtype: 'Select',
					label: __('Repeat cadence'),
					options: recurrenceLabels.join('\n'),
					reqd: 1,
					description: __('Choose how frequently this meeting repeats.')
				},
				{
					fieldname: 'occurrences',
					fieldtype: 'Int',
					label: __('Stop after (occurrences)'),
					reqd: 1,
					default: 6,
					description: __('Maximum {0} per batch.', [TEAM_MEETING_MAX_OCCURRENCES])
				},
				{ fieldname: 'preview_html', fieldtype: 'HTML' },
				{ fieldtype: 'Section Break', label: __('Participants') },
				{ fieldname: 'participants_html', fieldtype: 'HTML' }
			],
			primary_action_label: __('Schedule Meetings'),
			primary_action(values) {
				const repeatValue = recurrenceValueByLabel[values.repeat_option];
				if (!repeatValue) {
					frappe.msgprint(__('Select a repeat cadence.'));
					return;
				}

				const ayMeta = ayState[values.academic_year];
				if (!ayMeta) {
					frappe.msgprint(__('Please choose an Academic Year within range.'));
					return;
				}

				const occurrences = normalize_occurrences(values.occurrences);
				if (!values.start_time || !values.end_time) {
					frappe.msgprint(__('Start and end times are required.'));
					return;
				}

				dialog.disable_primary_action();

				const request = frappe.call({
					method: 'ifitwala_ed.setup.doctype.team.team.schedule_recurring_meetings',
					args: {
						team: frm.doc.name,
						academic_year: values.academic_year,
						start_date: values.start_date,
						start_time: values.start_time,
						end_time: values.end_time,
						repeat_option: repeatValue,
						occurrences,
						meeting_title: values.meeting_title,
						location: values.location,
						virtual_meeting_link: values.virtual_meeting_link,
						meeting_category: values.meeting_category
					},
					freeze: true,
					freeze_message: __('Creating meetings…')
				});
				request.then(r => {
						const payload = r.message || {};
						const createdCount = (payload.created || []).length;
						const failedCount = (payload.failed || []).length;
						const seriesLink = payload.series
							? `<a href="#Form/Meeting Series/${payload.series}">${frappe.utils.escape_html(payload.series_title || payload.series)}</a>`
							: '';
						let message = '';

						if (createdCount) {
							message += __(
								'Created {0} meeting(s) linked to {1}.',
								[createdCount, seriesLink || __('the meeting series')]
							);
						} else {
							message += __('No meetings were created.');
						}

						if (failedCount) {
							message += '<br>' + __('{0} occurrence(s) could not be created.', [failedCount]);
						}

						frappe.msgprint({
							title: __('Scheduler result'),
							message,
							indicator: createdCount ? 'green' : 'orange'
						});

						dialog.hide();
						frm.reload_doc();
					});
				request.always(() => {
					dialog.enable_primary_action();
				});
			}
		});

		const ayState = {};
		const heroHtml = render_scheduler_hero(frm);
		dialog.fields_dict.intro_html.$wrapper.html(heroHtml);
		dialog.fields_dict.participants_html.$wrapper.html(render_participants_preview(activeMembers));
		dialog.$wrapper.addClass('team-meeting-scheduler');

		dialog.fields_dict.academic_year.get_query = () => ({
			query: 'ifitwala_ed.utilities.link_queries.academic_year_link_query',
			filters: {
				school: frm.doc.school,
			},
		});

		dialog.set_df_property('meeting_category', 'options', ['', ...meetingCategoryOptions].join('\n'));

		dialog.set_value('meeting_title', `${frm.doc.team_name || frm.doc.team_code || frm.doc.name} ${__('Meeting')}`);
		dialog.set_value('repeat_option', TEAM_MEETING_RECURRENCE_OPTIONS[0].label);
		dialog.set_value('start_date', frappe.datetime.nowdate());

		const updateAcademicYearHint = () => {
			const ayName = dialog.get_value('academic_year');
			const ayMeta = ayState[ayName];
			const target = dialog.fields_dict.ay_window.$wrapper;
			if (!ayName) {
				target.html(`<div class="team-scheduler-empty">${__('Pick an academic year to see its bounds.')}</div>`);
				return;
			}
			if (!ayMeta) {
				target.html(`<div class="team-scheduler-empty">${__('Academic year metadata is loading…')}</div>`);
				return;
			}
			const start = frappe.datetime.str_to_user(ayMeta.year_start_date);
			const end = frappe.datetime.str_to_user(ayMeta.year_end_date);
			const providerName = ayMeta.school_name || ayMeta.school || __('Unknown School');
			const inherited = frm.doc.school && ayMeta.source_school && frm.doc.school !== ayMeta.source_school;
			const inheritedLabel = inherited
				? `<div class="team-scheduler-ay-card__note">${__('Inherited from {0}', [
						frappe.utils.escape_html(ayMeta.source_school_name || ayMeta.source_school)
				  ])}</div>`
				: '';
			target.html(
				`<div class="team-scheduler-ay-card">
					<div>
						<div class="team-scheduler-ay-card__title">${frappe.utils.escape_html(ayMeta.label || ayName)}</div>
						<div class="team-scheduler-ay-card__range">${start} → ${end}</div>
						<div class="team-scheduler-ay-card__provider">${__('Hosted by {0}', [
							frappe.utils.escape_html(providerName)
						])}</div>
					</div>
					<span class="badge text-bg-light">${__('Aligned to {0}', [
						frappe.utils.escape_html(frm.doc.school || __('school'))
					])}</span>
					${inheritedLabel}
				</div>`
			);
		};

		const updatePreview = () => {
			const values = collect_preview_values(dialog);
			const previewWrapper = dialog.fields_dict.preview_html.$wrapper;
			if (!values) {
				previewWrapper.html(
					`<div class="team-scheduler-empty">${__('Fill out the form to preview your schedule.')}</div>`
				);
				return;
			}
			const ayMeta = ayState[values.academic_year];

			if (!values.academic_year || !ayMeta) {
				previewWrapper.html(`<div class="team-scheduler-empty">${__('Complete the fields above to see the timeline.')}</div>`);
				return;
			}

			const repeatValue = recurrenceValueByLabel[values.repeat_option] || TEAM_MEETING_RECURRENCE_OPTIONS[0].value;
			const normalizedOccurrences = normalize_occurrences(values.occurrences);
			const rawOccurrences =
				typeof values.occurrences === 'number' ? values.occurrences : parseInt(values.occurrences, 10);
			if (!Number.isFinite(rawOccurrences) || rawOccurrences !== normalizedOccurrences) {
				dialog.set_value('occurrences', normalizedOccurrences);
				return;
			}

			if (!values.start_date || !values.start_time || !values.end_time) {
				previewWrapper.html(
					`<div class="team-scheduler-empty">${__('Set a start date and time range to preview the series.')}</div>`
				);
				return;
			}

			const startDate = dayjs(values.start_date);
			if (!startDate.isValid()) {
				previewWrapper.html(`<div class="team-scheduler-empty">${__('Start date is invalid.')}</div>`);
				return;
			}

			const plan = build_occurrence_plan({
				startDate,
				recurrence: repeatValue,
				requested: normalizedOccurrences,
				academicYear: ayMeta
			});

			if (!plan.dates.length) {
				previewWrapper.html(
					`<div class="team-scheduler-empty">${__('This cadence would extend past the academic year. Pick an earlier date or reduce the count.')}</div>`
				);
				return;
			}

			const recurrenceLabel = recurrenceLabelByValue[repeatValue] || values.repeat_option;
			const summary = render_occurrence_preview(plan, {
				recurrenceLabel,
				startTime: values.start_time,
				endTime: values.end_time,
				academicYear: ayMeta
			});
			previewWrapper.html(summary);
		};

		['academic_year', 'start_date', 'start_time', 'end_time', 'repeat_option', 'occurrences'].forEach(fieldname => {
			const df = dialog.fields_dict[fieldname];
			if (!df) return;

			const handler = () => {
				if (fieldname === 'academic_year') {
					updateAcademicYearHint();
				}
				updatePreview();
			};

			df.df.onchange = handler;
		});

		dialog.fields_dict.occurrences.$input?.attr('min', 1).attr('max', TEAM_MEETING_MAX_OCCURRENCES);

		const loadAcademicYears = () => {
			dialog.disable_primary_action();
			const ayRequest = frappe.call({
				method: 'ifitwala_ed.setup.doctype.team.team.get_schedulable_academic_years',
				args: { team: frm.doc.name }
			});
			ayRequest.then(r => {
					const rows = r.message || [];
					if (!rows.length) {
						dialog.fields_dict.ay_window.$wrapper.html(
							`<div class="team-scheduler-empty">${__('No current or upcoming academic years were found for this team.')}</div>`
						);
						return;
					}

					rows.forEach(ay => {
						ayState[ay.name] = ay;
					});

					dialog.set_value('academic_year', rows[0].name);
					updateAcademicYearHint();
					updatePreview();
				});
			ayRequest.always(() => {
				dialog.enable_primary_action();
			});
		};

		loadAcademicYears();
		dialog.show();
	});
}

function normalize_occurrences(value) {
	const numeric = parseInt(value, 10);
	if (!numeric || numeric < 1) {
		return 1;
	}
	return Math.min(numeric, TEAM_MEETING_MAX_OCCURRENCES);
}

function render_scheduler_hero(frm) {
	const color = frm.doc.meeting_color || '#364FC7';
	const initials = (frm.doc.team_name || frm.doc.team_code || frm.doc.name || 'T').charAt(0).toUpperCase();
	const title = frappe.utils.escape_html(frm.doc.team_name || frm.doc.name);
	const meta = frappe.utils.escape_html(frm.doc.school || frm.doc.organization || __('No school set'));

	return `
		<div class="team-scheduler-hero">
			<div class="team-scheduler-hero__avatar" style="background:${color}1A;color:${color}">
				${initials}
			</div>
			<div>
				<div class="team-scheduler-hero__title">${title}</div>
				<div class="team-scheduler-hero__meta">${meta}</div>
			</div>
		</div>
	`;
}

function render_participants_preview(members) {
	if (!members.length) {
		return `<div class="team-scheduler-empty">${__('No members yet. Add a few teammates first.')}</div>`;
	}

	const chips = members
		.map(member => {
			const name = frappe.utils.escape_html(member.member_name || member.employee || member.member);
			const role = frappe.utils.escape_html(member.role_in_team || __('Member'));
			return `
				<li class="team-scheduler-chip">
					<span class="team-scheduler-chip__name">${name}</span>
					<span class="team-scheduler-chip__role">${role}</span>
				</li>
			`;
		})
		.join('');

	return `
		<div class="team-scheduler-participants">
			<div class="team-scheduler-participants__heading">
				${__('Everyone gets invited ({0})', [members.length])}
			</div>
			<ul class="team-scheduler-chip-list">${chips}</ul>
		</div>
	`;
}

function build_occurrence_plan({ startDate, recurrence, requested, academicYear }) {
	const ayStart = dayjs(academicYear.year_start_date);
	const ayEnd = dayjs(academicYear.year_end_date);
	const meta = TEAM_MEETING_RECURRENCE_META[recurrence] || TEAM_MEETING_RECURRENCE_META.weekly;
	const dates = [];
	let cursor = startDate;
	let guard = 0;

	while (!cursor.isAfter(ayEnd) && dates.length < requested && guard < TEAM_MEETING_MAX_OCCURRENCES * 2) {
		if (cursor.isBefore(ayStart)) {
			cursor = ayStart;
		}

		if (cursor.isAfter(ayEnd)) {
			break;
		}

		dates.push(cursor);
		cursor = meta.unit === 'week' ? cursor.add(meta.step, 'week') : cursor.add(meta.step, 'month');
		guard++;
	}

	return {
		dates,
		truncated: dates.length < requested,
		meta
	};
}

function render_occurrence_preview(plan, context) {
	const { recurrenceLabel, startTime, endTime, academicYear } = context;
	const total = plan.dates.length;
	const humanStart = dayjs(academicYear.year_start_date).format('MMM D, YYYY');
	const humanEnd = dayjs(academicYear.year_end_date).format('MMM D, YYYY');
	const prettyTime = format_time_range(startTime, endTime);
	const duration = format_duration_minutes(startTime, endTime);

	const listItems = plan.dates.slice(0, 5).map((date, idx) => {
		const label = date.format('ddd, MMM D');
		return `
			<li class="team-scheduler-occurrence">
				<span class="team-scheduler-occurrence__index">#${idx + 1}</span>
				<div>
					<div class="team-scheduler-occurrence__label">${label}</div>
					<div class="team-scheduler-occurrence__time">${prettyTime}</div>
				</div>
			</li>
		`;
	});

	const remainder = Math.max(plan.dates.length - 5, 0);
	const truncated = plan.truncated
		? `<div class="team-scheduler-note is-warning">${__('Series stops early because the academic year ends on {0}.', [
				dayjs(academicYear.year_end_date).format('MMM D, YYYY')
		  ])}</div>`
		: '';

	return `
		<div class="team-scheduler-summary">
			<div>
				<div class="team-scheduler-summary__count">${total}</div>
				<div class="team-scheduler-summary__label">${__('meetings will be created')}</div>
			</div>
			<div class="team-scheduler-summary__meta">
				<span>${recurrenceLabel}</span>
				<span>${prettyTime}</span>
				${duration ? `<span>${duration}</span>` : ''}
			</div>
		</div>
		<div class="team-scheduler-summary__window">
			${humanStart} → ${humanEnd}
		</div>
		<ol class="team-scheduler-occurrence-list">
			${listItems.join('')}
		</ol>
		${remainder ? `<div class="team-scheduler-note">${__('+{0} more occurrence(s)', [remainder])}</div>` : ''}
		${truncated}
	`;
}

function format_time_range(startTime, endTime) {
	if (!startTime || !endTime) {
		return __('Set a time range');
	}
	const start = frappe.datetime.get_formatted_time(startTime);
	const end = frappe.datetime.get_formatted_time(endTime);
	return `${start} → ${end}`;
}

function format_duration_minutes(startTime, endTime) {
	if (!startTime || !endTime) {
		return '';
	}
	const start = dayjs(`2000-01-01 ${startTime}`);
	const end = dayjs(`2000-01-01 ${endTime}`);
	const minutes = end.diff(start, 'minute');
	if (minutes <= 0) {
		return '';
	}
	return __('{0} min', [minutes]);
}

function ensure_scheduler_styles() {
	if (document.getElementById('team-scheduler-style')) {
		return;
	}
	const style = document.createElement('style');
	style.id = 'team-scheduler-style';
	style.textContent = `
		.team-meeting-scheduler .modal-body {
			background: #f8fafc;
		}
		.team-scheduler-hero {
			display: flex;
			align-items: center;
			gap: 0.75rem;
			padding: 1rem;
			background: #fff;
			border: 1px solid #e2e8f0;
			border-radius: 16px;
			margin-bottom: 1rem;
		}
		.team-scheduler-hero__avatar {
			width: 48px;
			height: 48px;
			border-radius: 12px;
			display: flex;
			align-items: center;
			justify-content: center;
			font-weight: 600;
			font-size: 1.1rem;
		}
		.team-scheduler-hero__title {
			font-size: 1.05rem;
			font-weight: 600;
		}
		.team-scheduler-hero__meta {
			color: #475569;
			font-size: 0.9rem;
		}
		.team-scheduler-ay-card {
			margin-top: 0.5rem;
			padding: 0.75rem 1rem;
			background: #fff;
			border-radius: 12px;
			border: 1px solid #e2e8f0;
			display: flex;
			align-items: center;
			justify-content: space-between;
			gap: 1rem;
		}
		.team-scheduler-ay-card__title {
			font-weight: 600;
			margin-bottom: 0.25rem;
		}
		.team-scheduler-ay-card__range {
			color: #475569;
			font-size: 0.9rem;
		}
		.team-scheduler-ay-card__provider {
			color: #1d4ed8;
			font-size: 0.85rem;
			margin-top: 0.25rem;
		}
		.team-scheduler-ay-card__note {
			margin-top: 0.35rem;
			color: #b45309;
			font-size: 0.85rem;
		}
		.team-scheduler-empty {
			padding: 0.85rem;
			background: #fff;
			border-radius: 12px;
			border: 1px dashed #cbd5f5;
			color: #64748b;
			text-align: center;
		}
		.team-scheduler-participants__heading {
			font-weight: 600;
			margin-bottom: 0.5rem;
		}
		.team-scheduler-chip-list {
			list-style: none;
			padding: 0;
			margin: 0;
			display: grid;
			grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
			gap: 0.5rem;
		}
		.team-scheduler-chip {
			padding: 0.6rem 0.75rem;
			background: #fff;
			border-radius: 999px;
			border: 1px solid #e2e8f0;
			display: flex;
			flex-direction: column;
		}
		.team-scheduler-chip__name {
			font-weight: 600;
			font-size: 0.95rem;
		}
		.team-scheduler-chip__role {
			font-size: 0.8rem;
			color: #64748b;
			text-transform: uppercase;
			letter-spacing: 0.03em;
		}
		.team-scheduler-summary {
			background: #fff;
			border: 1px solid #e2e8f0;
			border-radius: 16px;
			padding: 1rem;
			display: flex;
			align-items: center;
			justify-content: space-between;
			gap: 1rem;
			margin-bottom: 0.75rem;
		}
		.team-scheduler-summary__count {
			font-size: 2.25rem;
			font-weight: 600;
			line-height: 1;
		}
		.team-scheduler-summary__label {
			color: #475569;
		}
		.team-scheduler-summary__meta {
			display: flex;
			flex-wrap: wrap;
			gap: 0.5rem;
			color: #475569;
		}
		.team-scheduler-summary__window {
			margin-bottom: 0.5rem;
			color: #475569;
			font-size: 0.9rem;
		}
		.team-scheduler-occurrence-list {
			list-style: none;
			padding: 0;
			margin: 0 0 0.5rem 0;
			display: flex;
			flex-direction: column;
			gap: 0.5rem;
		}
		.team-scheduler-occurrence {
			background: #fff;
			border: 1px solid #e2e8f0;
			border-radius: 10px;
			padding: 0.5rem 0.75rem;
			display: flex;
			gap: 0.75rem;
			align-items: center;
		}
		.team-scheduler-occurrence__index {
			font-weight: 600;
			color: #475569;
			width: 32px;
		}
		.team-scheduler-occurrence__label {
			font-weight: 500;
		}
		.team-scheduler-occurrence__time {
			color: #64748b;
			font-size: 0.9rem;
		}
		.team-scheduler-note {
			background: #fff7ed;
			color: #c2410c;
			padding: 0.65rem 0.75rem;
			border-radius: 10px;
			border: 1px solid #fed7aa;
			font-size: 0.9rem;
		}
		.team-scheduler-note.is-warning {
			background: #fff1f2;
			border-color: #fecdd3;
			color: #be123c;
		}
	`;
	document.head.appendChild(style);
}

function collect_preview_values(dialog) {
	if (!dialog) {
		return null;
	}
	const grab = fieldname => dialog.get_value ? dialog.get_value(fieldname) : null;
	return {
		academic_year: grab('academic_year'),
		start_date: grab('start_date'),
		start_time: grab('start_time'),
		end_time: grab('end_time'),
		repeat_option: grab('repeat_option'),
		occurrences: grab('occurrences'),
	};
}
