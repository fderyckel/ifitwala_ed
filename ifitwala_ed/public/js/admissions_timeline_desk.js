// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

(function () {
	const root = (window.ifitwala_ed = window.ifitwala_ed || {});

	const TIMELINE_METHOD = 'ifitwala_ed.api.admissions_timeline.get_admissions_timeline_context';
	const LOG_MESSAGE_METHOD = 'ifitwala_ed.api.admissions_crm.log_admission_message';
	const LOG_ACTIVITY_METHOD = 'ifitwala_ed.api.admissions_crm.record_admission_crm_activity';
	const VISIT_OPTIONS_METHOD =
		'ifitwala_ed.admission.doctype.admission_visit.admission_visit.get_admission_visit_schedule_options';
	const SCHEDULE_VISIT_METHOD =
		'ifitwala_ed.admission.doctype.admission_visit.admission_visit.schedule_admission_visit';
	const SEND_CASE_MESSAGE_METHOD =
		'ifitwala_ed.api.admissions_communication.send_admissions_case_message';
	const GET_OR_CREATE_PLAN_METHOD =
		'ifitwala_ed.admission.doctype.applicant_enrollment_plan.applicant_enrollment_plan.get_or_create_applicant_enrollment_plan';

	const ACTIVITY_TYPES = [
		'Call Attempt',
		'Reached',
		'No Answer',
		'Qualified',
		'Not Interested',
		'Booked Tour',
		'Attended Tour',
		'Follow-up Scheduled',
		'Archived',
		'Note',
	];

	function clean(value) {
		const text = String(value || '').trim();
		return text || '';
	}

	function escapeHtml(value) {
		return String(value || '')
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;')
			.replace(/'/g, '&#039;');
	}

	function randomId(prefix) {
		if (window.crypto && typeof window.crypto.randomUUID === 'function') {
			return `${prefix}-${window.crypto.randomUUID()}`;
		}
		return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
	}

	function safeOpenUrl(url) {
		const value = clean(url);
		if (!value || value.indexOf('/private/') === 0) {
			return '';
		}
		return value;
	}

	function routeToUrl(url) {
		const value = safeOpenUrl(url);
		if (!value) {
			frappe.msgprint(__('Open unavailable: no permitted destination returned.'));
			return;
		}
		window.open(value, '_blank', 'noopener,noreferrer');
	}

	function actionLabel(actionId) {
		return clean(actionId)
			.split('_')
			.filter(Boolean)
			.map(part => part.charAt(0).toUpperCase() + part.slice(1))
			.join(' ');
	}

	function kindLabel(kind) {
		const value = clean(kind);
		if (value === 'intake') return __('Intake');
		if (value === 'message') return __('Message');
		if (value === 'touchpoint') return __('Touchpoint');
		if (value === 'visit') return __('Visit');
		if (value === 'applicant') return __('Applicant');
		if (value === 'offer') return __('Offer');
		if (value === 'deposit') return __('Deposit');
		if (value === 'enrollment') return __('Enrollment');
		if (!value) return __('Admissions');
		return actionLabel(value);
	}

	function actorLabel(actor) {
		const value = clean(actor);
		if (value === 'Inbound') return __('Family');
		if (value === 'Outbound') return __('Staff');
		if (value === 'System') return __('System');
		if (value === 'applicant') return __('Applicant');
		if (value === 'staff') return __('Staff');
		return value;
	}

	function formatDateTime(value) {
		const text = clean(value);
		if (!text) return '';
		if (frappe.datetime && typeof frappe.datetime.str_to_user === 'function') {
			return frappe.datetime.str_to_user(text);
		}
		return text;
	}

	function getContextArgs(timeline, fallback) {
		const context = timeline?.context || {};
		const requested = fallback || {};
		const doctype = clean(context.doctype || requested.contextDoctype);
		const name = clean(context.name || requested.contextName);
		return {
			context_doctype: doctype,
			context_name: name,
			conversation: clean(context.conversation),
			inquiry: clean(context.inquiry || (doctype === 'Inquiry' ? name : '')),
			student_applicant: clean(
				context.student_applicant || (doctype === 'Student Applicant' ? name : '')
			),
			organization: clean(context.organization),
			school: clean(context.school),
		};
	}

	function visitContextArgs(context) {
		return {
			conversation: context.conversation || undefined,
			inquiry: context.inquiry || undefined,
			student_applicant: context.student_applicant || undefined,
			organization: context.organization || undefined,
			school: context.school || undefined,
		};
	}

	function timelineRequest(contextDoctype, contextName, limit) {
		return {
			context_doctype: contextDoctype,
			context_name: contextName,
			limit: limit || 50,
		};
	}

	function loadTimeline(contextDoctype, contextName, limit) {
		return frappe
			.call({
				method: TIMELINE_METHOD,
				args: timelineRequest(contextDoctype, contextName, limit),
				freeze: true,
				freeze_message: __('Loading admissions timeline…'),
			})
			.then(res => res?.message || {});
	}

	function findAction(timeline, actionId) {
		return (timeline?.actions || []).find(action => clean(action.id) === actionId) || null;
	}

	function actionButtonHtml(action, index) {
		const enabled = Boolean(action?.enabled);
		const label = escapeHtml(action?.label || actionLabel(action?.id));
		const reason =
			!enabled && action?.disabled_reason
				? `<small>${escapeHtml(action.disabled_reason)}</small>`
				: '';
		return `
			<button
				type="button"
				class="btn btn-xs ${enabled ? 'btn-secondary' : 'btn-default'} admissions-timeline-action"
				data-action-index="${index}"
				${enabled ? '' : 'disabled'}
				title="${escapeHtml(enabled ? label : action?.disabled_reason || label)}"
			>
				${label}
				${reason}
			</button>
		`;
	}

	function ladderHtml(timeline) {
		const steps = timeline?.summary?.completion_ladder || [];
		if (!steps.length) {
			return '';
		}
		return `
			<div class="admissions-timeline-ladder">
				${steps
					.map(
						step => `
					<span class="admissions-timeline-step admissions-timeline-step-${escapeHtml(step.state || 'pending')}">
						${escapeHtml(step.label)}
					</span>
				`
					)
					.join('')}
			</div>
		`;
	}

	function actionsHtml(timeline) {
		const actions = (timeline?.actions || []).filter(
			action => clean(action.id) !== 'open_timeline'
		);
		if (!actions.length) {
			return '';
		}
		return `
			<div class="admissions-timeline-actions">
				${actions.map(actionButtonHtml).join('')}
			</div>
		`;
	}

	function itemsHtml(timeline) {
		const items = timeline?.items || [];
		if (!items.length) {
			return `<div class="text-muted">${__('No admissions timeline items yet.')}</div>`;
		}
		return `
			<ol class="admissions-timeline-items">
				${items
					.map((item, index) => {
						const url = safeOpenUrl(item.open_url);
						return `
						<li class="admissions-timeline-item">
							<div class="admissions-timeline-item-marker admissions-timeline-item-marker-${escapeHtml(item.kind || 'item')}"></div>
							<div class="admissions-timeline-item-body">
								<div class="admissions-timeline-item-top">
									<div>
										<div class="text-muted small">${escapeHtml(kindLabel(item.kind))}</div>
										<strong>${escapeHtml(item.title)}</strong>
									</div>
									<div class="text-muted small">${escapeHtml(formatDateTime(item.occurred_at))}</div>
								</div>
								${item.summary ? `<div class="admissions-timeline-item-summary">${escapeHtml(item.summary)}</div>` : ''}
								<div class="admissions-timeline-item-footer">
									<span class="text-muted small">${escapeHtml(actorLabel(item.actor))}</span>
									${
										url
											? `
										<button type="button" class="btn btn-xs btn-link admissions-timeline-open" data-item-index="${index}">
											${__('Open')}
										</button>
									`
											: ''
									}
								</div>
							</div>
						</li>
					`;
					})
					.join('')}
			</ol>
		`;
	}

	function renderTimelineHtml(timeline) {
		const label = timeline?.context?.label || __('Admissions relationship');
		const latest = formatDateTime(timeline?.summary?.latest_at);
		const needsReply = timeline?.summary?.needs_reply
			? `<span class="indicator-pill red">${__('Needs reply')}</span>`
			: '';
		const hasMore = timeline?.has_more
			? `<div class="text-muted small">${__('More timeline items are available after the current page limit.')}</div>`
			: '';

		return `
			<style>
				.admissions-timeline-desk { display: grid; gap: 14px; min-width: 0; }
				.admissions-timeline-head { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
				.admissions-timeline-title { min-width: 0; }
				.admissions-timeline-title h4 { margin: 2px 0 0; overflow-wrap: anywhere; }
				.admissions-timeline-ladder, .admissions-timeline-actions { display: flex; flex-wrap: wrap; gap: 6px; }
				.admissions-timeline-step { border: 1px solid var(--border-color); border-radius: 999px; padding: 4px 8px; font-size: 12px; background: var(--fg-color); }
				.admissions-timeline-step-done { border-color: var(--green-400); color: var(--green-700); }
				.admissions-timeline-step-current { border-color: var(--blue-400); color: var(--blue-700); }
				.admissions-timeline-action small { display: block; margin-top: 2px; max-width: 220px; white-space: normal; }
				.admissions-timeline-items { display: grid; gap: 10px; list-style: none; margin: 0; padding: 0; }
				.admissions-timeline-item { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 10px; }
				.admissions-timeline-item-marker { width: 10px; height: 10px; border-radius: 999px; margin-top: 12px; background: var(--blue-500); box-shadow: 0 0 0 4px var(--blue-100); }
				.admissions-timeline-item-marker-message { background: var(--purple-500); box-shadow: 0 0 0 4px var(--purple-100); }
				.admissions-timeline-item-marker-visit, .admissions-timeline-item-marker-offer, .admissions-timeline-item-marker-deposit { background: var(--green-500); box-shadow: 0 0 0 4px var(--green-100); }
				.admissions-timeline-item-body { border: 1px solid var(--border-color); border-radius: 8px; padding: 10px; min-width: 0; }
				.admissions-timeline-item-top, .admissions-timeline-item-footer { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
				.admissions-timeline-item-summary { margin-top: 6px; overflow-wrap: anywhere; }
				.admissions-timeline-item-footer { align-items: center; margin-top: 8px; }
			</style>
			<div class="admissions-timeline-desk">
				<div class="admissions-timeline-head">
					<div class="admissions-timeline-title">
						<div class="text-muted small">${__('Timeline')}</div>
						<h4>${escapeHtml(label)}</h4>
						${latest ? `<div class="text-muted small">${escapeHtml(__('Latest {0}', [latest]))}</div>` : ''}
					</div>
					${needsReply}
				</div>
				${ladderHtml(timeline)}
				${actionsHtml(timeline)}
				${itemsHtml(timeline)}
				${hasMore}
			</div>
		`;
	}

	function bindTimelineDialog(dialog, timeline, state) {
		const field = dialog.get_field('timeline_html');
		const wrapper = field?.$wrapper;
		if (!wrapper?.length) {
			return;
		}

		wrapper.off('click.admissionsTimeline');
		wrapper.on('click.admissionsTimeline', '.admissions-timeline-open', function () {
			const index = Number($(this).attr('data-item-index'));
			const item = timeline?.items?.[index];
			if (item) {
				routeToUrl(item.open_url);
			}
		});
		wrapper.on('click.admissionsTimeline', '.admissions-timeline-action', function () {
			const index = Number($(this).attr('data-action-index'));
			const actions = (timeline?.actions || []).filter(
				action => clean(action.id) !== 'open_timeline'
			);
			const action = actions[index];
			if (action) {
				handleTimelineAction(action, state);
			}
		});
	}

	function setTimelineDialogContent(dialog, timeline, state) {
		const field = dialog.get_field('timeline_html');
		if (!field?.$wrapper) {
			return;
		}
		field.$wrapper.html(renderTimelineHtml(timeline));
		bindTimelineDialog(dialog, timeline, state);
	}

	function openTimelineDialog(options) {
		const contextDoctype = clean(options?.contextDoctype);
		const contextName = clean(options?.contextName);
		if (!contextDoctype || !contextName) {
			frappe.msgprint(__('Admissions timeline context is missing.'));
			return;
		}

		const state = {
			sourceFrm: options?.sourceFrm || null,
			contextDoctype,
			contextName,
			timeline: null,
		};

		const dialog = new frappe.ui.Dialog({
			title: __('Admissions Timeline'),
			size: 'large',
			fields: [{ fieldname: 'timeline_html', fieldtype: 'HTML' }],
			primary_action_label: __('Refresh'),
			primary_action() {
				refreshTimelineDialog(dialog, state);
			},
		});

		dialog.show();
		dialog
			.get_field('timeline_html')
			.$wrapper.html(`<div class="text-muted">${__('Loading admissions timeline…')}</div>`);
		refreshTimelineDialog(dialog, state);
	}

	function refreshTimelineDialog(dialog, state) {
		dialog.disable_primary_action();
		loadTimeline(state.contextDoctype, state.contextName, 50)
			.then(timeline => {
				state.timeline = timeline;
				setTimelineDialogContent(dialog, timeline, state);
			})
			.catch(err => {
				const field = dialog.get_field('timeline_html');
				field?.$wrapper?.html(`
					<div class="alert alert-danger">
						${escapeHtml(err?.message || __('Unable to load admissions timeline.'))}
					</div>
				`);
			})
			.then(() => dialog.enable_primary_action());
	}

	function loadContextThenRun(options, actionId) {
		const contextDoctype = clean(options?.contextDoctype);
		const contextName = clean(options?.contextName);
		if (!contextDoctype || !contextName) {
			frappe.msgprint(__('Admissions context is missing.'));
			return;
		}
		loadTimeline(contextDoctype, contextName, 50)
			.then(timeline => {
				const action = findAction(timeline, actionId);
				if (!action) {
					frappe.msgprint(
						__('This contextual action is not available for the current admissions record.')
					);
					return;
				}
				handleTimelineAction(action, {
					sourceFrm: options?.sourceFrm || null,
					contextDoctype,
					contextName,
					timeline,
				});
			})
			.catch(err => {
				frappe.msgprint(err?.message || __('Unable to load admissions timeline.'));
			});
	}

	function handleTimelineAction(action, state) {
		if (!action?.enabled) {
			frappe.msgprint(action?.disabled_reason || __('This timeline action is blocked.'));
			return;
		}

		const actionId = clean(action.id);
		if (actionId === 'log_message') {
			promptLogMessage(state);
			return;
		}
		if (actionId === 'log_activity') {
			promptLogActivity(state);
			return;
		}
		if (actionId === 'schedule_visit') {
			openVisitDialog(state);
			return;
		}
		if (actionId === 'message_family') {
			promptMessageFamily(state);
			return;
		}
		if (actionId === 'manage_offer') {
			openEnrollmentPlan(state);
			return;
		}
		if (actionId === 'check_deposit') {
			openDepositContext(action, state);
			return;
		}
		if (actionId === 'promote') {
			promoteApplicant(action, state);
			return;
		}
		if (actionId === 'invite_to_apply') {
			inviteToApply(action, state);
			return;
		}
		if (actionId === 'archive') {
			archiveContext(action, state);
			return;
		}

		frappe.msgprint(__('This contextual action is not available in Desk yet.'));
	}

	function promptLogMessage(state) {
		const context = getContextArgs(state.timeline, state);
		const dialog = new frappe.ui.Dialog({
			title: __('Log Admissions Message'),
			fields: [
				{
					label: __('Message'),
					fieldname: 'body',
					fieldtype: 'Text',
					reqd: 1,
					description: __('Record the admissions reply or message outcome.'),
				},
			],
			primary_action_label: __('Log Message'),
			primary_action(values) {
				const body = clean(values.body);
				if (!body) {
					frappe.msgprint(__('Message is required.'));
					return;
				}
				dialog.disable_primary_action();
				frappe
					.call({
						method: LOG_MESSAGE_METHOD,
						args: {
							conversation: context.conversation || undefined,
							inquiry: context.inquiry || undefined,
							student_applicant: context.student_applicant || undefined,
							organization: context.organization || undefined,
							school: context.school || undefined,
							direction: 'Outbound',
							message_type: 'Text',
							delivery_status: 'Logged',
							body,
							client_request_id: randomId('desk-admission-message'),
						},
						freeze: true,
						freeze_message: __('Logging message...'),
					})
					.then(() => {
						frappe.show_alert({ message: __('Message logged.'), indicator: 'green' });
						dialog.hide();
						state.sourceFrm?.reload_doc?.();
					})
					.catch(err => {
						frappe.msgprint(err?.message || __('Unable to log message.'));
					})
					.then(() => dialog.enable_primary_action());
			},
		});
		dialog.show();
	}

	function promptLogActivity(state) {
		const context = getContextArgs(state.timeline, state);
		if (!context.conversation) {
			frappe.msgprint(
				__('Log a message first so an admissions conversation exists for this activity.')
			);
			return;
		}
		const dialog = new frappe.ui.Dialog({
			title: __('Log Admissions Activity'),
			fields: [
				{
					label: __('Activity Type'),
					fieldname: 'activity_type',
					fieldtype: 'Select',
					options: ACTIVITY_TYPES.join('\n'),
					reqd: 1,
					default: 'Reached',
				},
				{
					label: __('Outcome'),
					fieldname: 'outcome',
					fieldtype: 'Data',
				},
				{
					label: __('Next Action On'),
					fieldname: 'next_action_on',
					fieldtype: 'Date',
				},
				{
					label: __('Note'),
					fieldname: 'note',
					fieldtype: 'Small Text',
				},
			],
			primary_action_label: __('Log Activity'),
			primary_action(values) {
				const activityType = clean(values.activity_type);
				if (!activityType) {
					frappe.msgprint(__('Activity Type is required.'));
					return;
				}
				dialog.disable_primary_action();
				frappe
					.call({
						method: LOG_ACTIVITY_METHOD,
						args: {
							conversation: context.conversation,
							activity_type: activityType,
							outcome: clean(values.outcome) || undefined,
							note: clean(values.note) || undefined,
							next_action_on: clean(values.next_action_on) || undefined,
							client_request_id: randomId('desk-admission-activity'),
						},
						freeze: true,
						freeze_message: __('Logging activity...'),
					})
					.then(() => {
						frappe.show_alert({ message: __('Activity logged.'), indicator: 'green' });
						dialog.hide();
						state.sourceFrm?.reload_doc?.();
					})
					.catch(err => {
						frappe.msgprint(err?.message || __('Unable to log activity.'));
					})
					.then(() => dialog.enable_primary_action());
			},
		});
		dialog.show();
	}

	function openVisitDialog(state) {
		const context = getContextArgs(state.timeline, state);
		frappe
			.call({
				method: VISIT_OPTIONS_METHOD,
				args: visitContextArgs(context),
				freeze: true,
				freeze_message: __('Loading visit options…'),
			})
			.then(res => {
				renderVisitDialog(state, res?.message || {});
			})
			.catch(err => {
				frappe.msgprint({
					title: __('Unable to schedule visit'),
					indicator: 'red',
					message: err?.message || __('Please try again.'),
				});
			});
	}

	function renderVisitDialog(state, payload) {
		const context = getContextArgs(payload, state);
		const defaults = payload?.defaults || {};
		const roomRows = Array.isArray(payload?.rooms) ? payload.rooms : [];
		const roomOptions = ['', ...roomRows.map(row => clean(row.value)).filter(Boolean)].join('\n');
		const dialog = new frappe.ui.Dialog({
			title: __('Schedule Admissions Visit'),
			size: 'large',
			fields: [
				{
					label: __('Visit Date'),
					fieldname: 'visit_date',
					fieldtype: 'Date',
					reqd: 1,
					default: defaults.date || frappe.datetime.get_today(),
				},
				{
					label: __('Start Time'),
					fieldname: 'start_time',
					fieldtype: 'Time',
					reqd: 1,
					default: defaults.start_time || '09:00:00',
				},
				{
					label: __('Duration (minutes)'),
					fieldname: 'duration_minutes',
					fieldtype: 'Int',
					reqd: 1,
					default: defaults.duration_minutes || 45,
				},
				{ fieldname: 'visit_column_break', fieldtype: 'Column Break' },
				{
					label: __('Visit Type'),
					fieldname: 'visit_type',
					fieldtype: 'Select',
					options: (
						payload?.visit_types || [
							'Family Tour',
							'Student Tour',
							'Open Day',
							'School Visit',
							'Other',
						]
					).join('\n'),
					default: defaults.visit_type || 'Family Tour',
				},
				{
					label: __('Mode'),
					fieldname: 'visit_mode',
					fieldtype: 'Select',
					options: (payload?.visit_modes || ['In Person', 'Online', 'Phone']).join('\n'),
					default: defaults.visit_mode || 'In Person',
				},
				{
					label: __('Room'),
					fieldname: 'location',
					fieldtype: 'Select',
					options: roomOptions,
					description: roomRows.length
						? __('Required for in-person visits.')
						: __('No schedulable rooms are available for this school.'),
				},
				{
					label: __('Lead User'),
					fieldname: 'lead_user',
					fieldtype: 'Link',
					options: 'User',
					reqd: 1,
					default: defaults.lead_user || frappe.session.user,
				},
				{
					label: __('Party Size'),
					fieldname: 'party_size',
					fieldtype: 'Int',
				},
				{
					label: __('Internal Notes'),
					fieldname: 'internal_notes',
					fieldtype: 'Small Text',
				},
				{
					fieldname: 'suggestions_html',
					fieldtype: 'HTML',
				},
			],
			primary_action_label: __('Schedule Visit'),
			primary_action(values) {
				const visitDate = clean(values.visit_date);
				const startTime = clean(values.start_time);
				const duration = Number(values.duration_minutes || 0);
				if (!visitDate || !startTime) {
					frappe.msgprint(__('Visit date and start time are required.'));
					return;
				}
				if (!duration || duration <= 0) {
					frappe.msgprint(__('Duration must be a positive number.'));
					return;
				}
				if (clean(values.visit_mode) === 'In Person' && !clean(values.location)) {
					frappe.msgprint(__('Please select a room for an in-person visit.'));
					return;
				}
				dialog.disable_primary_action();
				frappe
					.call({
						method: SCHEDULE_VISIT_METHOD,
						args: {
							conversation: context.conversation || undefined,
							inquiry: context.inquiry || undefined,
							student_applicant: context.student_applicant || undefined,
							organization: context.organization || undefined,
							school: context.school || undefined,
							starts_on: `${visitDate} ${startTime}`,
							duration_minutes: duration,
							visit_type: values.visit_type,
							visit_mode: values.visit_mode,
							location: values.location,
							lead_user: values.lead_user,
							party_size: values.party_size,
							internal_notes: values.internal_notes,
						},
						freeze: true,
						freeze_message: __('Scheduling visit...'),
					})
					.then(res => {
						const result = res?.message || {};
						if (result.ok) {
							frappe.show_alert({
								message: __('Admissions visit scheduled.'),
								indicator: 'green',
							});
							dialog.hide();
							state.sourceFrm?.reload_doc?.();
							return;
						}
						renderVisitSuggestions(dialog, result.suggestions || []);
						frappe.msgprint({
							title: __('Selected Time Unavailable'),
							indicator: 'orange',
							message: result.message || __('The selected time is not available.'),
						});
					})
					.catch(err => {
						frappe.msgprint(err?.message || __('Unable to schedule visit.'));
					})
					.then(() => dialog.enable_primary_action());
			},
		});
		renderVisitSuggestions(dialog, []);
		dialog.show();
	}

	function renderVisitSuggestions(dialog, suggestions) {
		const field = dialog.get_field('suggestions_html');
		if (!field?.$wrapper) {
			return;
		}
		if (!Array.isArray(suggestions) || !suggestions.length) {
			field.$wrapper.html(
				`<div class="text-muted small">${__('No suggested free times yet.')}</div>`
			);
			return;
		}
		const rows = suggestions
			.map(slot => `<li>${escapeHtml(slot?.label || slot?.start || '')}</li>`)
			.join('');
		field.$wrapper.html(`
			<div class="small">
				<div>${__('Suggested free times')}:</div>
				<ol style="padding-left: 18px;">${rows}</ol>
			</div>
		`);
	}

	function promptMessageFamily(state) {
		const context = getContextArgs(state.timeline, state);
		if (!context.student_applicant) {
			frappe.msgprint(__('Message Family requires a Student Applicant context.'));
			return;
		}
		const dialog = new frappe.ui.Dialog({
			title: __('Message Family'),
			fields: [
				{
					label: __('Message'),
					fieldname: 'body',
					fieldtype: 'Text',
					reqd: 1,
				},
				{
					label: __('Visible to applicant portal'),
					fieldname: 'applicant_visible',
					fieldtype: 'Check',
					default: 1,
				},
			],
			primary_action_label: __('Send Message'),
			primary_action(values) {
				const body = clean(values.body);
				if (!body) {
					frappe.msgprint(__('Message is required.'));
					return;
				}
				dialog.disable_primary_action();
				frappe
					.call({
						method: SEND_CASE_MESSAGE_METHOD,
						args: {
							context_doctype: 'Student Applicant',
							context_name: context.student_applicant,
							body,
							applicant_visible: values.applicant_visible ? 1 : 0,
							client_request_id: randomId('desk-admission-case-message'),
						},
						freeze: true,
						freeze_message: __('Sending message...'),
					})
					.then(() => {
						frappe.show_alert({ message: __('Message sent.'), indicator: 'green' });
						dialog.hide();
						state.sourceFrm?.reload_doc?.();
					})
					.catch(err => {
						frappe.msgprint(err?.message || __('Unable to send message.'));
					})
					.then(() => dialog.enable_primary_action());
			},
		});
		dialog.show();
	}

	function openEnrollmentPlan(state) {
		const context = getContextArgs(state.timeline, state);
		if (!context.student_applicant) {
			frappe.msgprint(__('Manage Offer requires a Student Applicant context.'));
			return;
		}
		frappe
			.call({
				method: GET_OR_CREATE_PLAN_METHOD,
				args: { student_applicant: context.student_applicant },
				freeze: true,
				freeze_message: __('Opening offer...'),
			})
			.then(res => {
				const name = res?.message?.name;
				if (name) {
					frappe.set_route('Form', 'Applicant Enrollment Plan', name);
				}
			})
			.catch(err => {
				frappe.msgprint(err?.message || __('Unable to open the offer.'));
			});
	}

	function openDepositContext(action, state) {
		const target = clean(action?.target);
		const context = getContextArgs(state.timeline, state);
		if (target && target !== context.student_applicant) {
			frappe.set_route('Form', 'Applicant Enrollment Plan', target);
			return;
		}
		openEnrollmentPlan(state);
	}

	function promoteApplicant(action, state) {
		const target =
			clean(action?.target) || getContextArgs(state.timeline, state).student_applicant;
		const frm = state.sourceFrm;
		if (frm?.doctype === 'Student Applicant' && clean(frm.doc?.name) === target) {
			frappe.confirm(__('Promote this applicant to Student?'), () => {
				frm
					.call('promote_to_student')
					.then(() => frm.reload_doc())
					.catch(err => frappe.msgprint(err?.message || __('Unable to promote applicant.')));
			});
			return;
		}
		if (target) {
			frappe.set_route('Form', 'Student Applicant', target);
			frappe.show_alert({
				message: __('Open the applicant form and use Promote when ready.'),
				indicator: 'blue',
			});
		}
	}

	function inviteToApply(action, state) {
		const target = clean(action?.target) || getContextArgs(state.timeline, state).inquiry;
		const frm = state.sourceFrm;
		if (
			frm?.doctype === 'Inquiry' &&
			clean(frm.doc?.name) === target &&
			typeof frm.trigger === 'function'
		) {
			frm.trigger('convert_to_applicant');
			return;
		}
		if (target) {
			frappe.set_route('Form', 'Inquiry', target);
			frappe.show_alert({
				message: __('Open the Inquiry form and use Invite to Apply.'),
				indicator: 'blue',
			});
		}
	}

	function archiveContext(action, state) {
		const context = getContextArgs(state.timeline, state);
		const target = clean(action?.target);
		const frm = state.sourceFrm;
		if (
			frm?.doctype === 'Inquiry' &&
			clean(frm.doc?.name) === target &&
			typeof frm.trigger === 'function'
		) {
			frm.trigger('archive');
			return;
		}
		if (context.conversation) {
			frappe.set_route('Form', 'Admission Conversation', context.conversation);
			frappe.show_alert({
				message: __('Open the admissions conversation and archive it there.'),
				indicator: 'blue',
			});
			return;
		}
		if (target) {
			frappe.set_route('Form', 'Inquiry', target);
		}
	}

	root.admissionsTimeline = {
		openTimelineDialog,
		loadContextThenRun,
	};
})();
