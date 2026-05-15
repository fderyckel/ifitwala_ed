// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/school_settings/doctype/school_event/school_event.js

const LINKED_ANNOUNCEMENT_SUMMARY_METHOD =
	'ifitwala_ed.school_settings.doctype.school_event.school_event.get_school_event_linked_announcement_summary';
const PUBLISH_LINKED_ANNOUNCEMENT_METHOD =
	'ifitwala_ed.school_settings.doctype.school_event.school_event.publish_school_event_linked_announcement';

const LINKED_ANNOUNCEMENT_STATUS_COLORS = {
	Draft: '#475569',
	Scheduled: '#a16207',
	Published: '#166534',
	Archived: '#6b7280',
};

frappe.ui.form.on('School Event', {
	onload(frm) {
		set_reference_type_query(frm);
	},

	refresh(frm) {
		add_reference_jump_button(frm);
		sync_reference_field_lock(frm);
		toggle_reference_section_mode(frm);
		render_linked_announcement_block(frm);
		toggle_participants_visibility(frm);
	},

	reference_type(frm) {
		sync_reference_field_lock(frm);
		toggle_reference_section_mode(frm);
		render_linked_announcement_block(frm);
	},

	reference_name(frm) {
		sync_reference_field_lock(frm);
		toggle_reference_section_mode(frm);
		render_linked_announcement_block(frm);
	},
});

// Child row event
frappe.ui.form.on('School Event Audience', {
	audience_type(frm, cdt, cdn) {
		toggle_participants_visibility(frm);
	},
});

function set_reference_type_query(frm) {
	if (!frm.fields_dict.reference_type) return;

	frm.set_query('reference_type', () => ({
		filters: {
			issingle: 0,
			name: ['!=', 'Org Communication'],
		},
	}));
}

function add_reference_jump_button(frm) {
	if (frm.is_new() || !frm.doc.reference_type || !frm.doc.reference_name) return;
	if (is_linked_announcement_reference(frm)) return;

	frm.add_custom_button(frm.doc.reference_name, () => {
		frappe.set_route('Form', frm.doc.reference_type, frm.doc.reference_name);
	});
}

function is_linked_announcement_reference(frm) {
	return frm.doc.reference_type === 'Org Communication' && Boolean(frm.doc.reference_name);
}

function toggle_reference_section_mode(frm) {
	const show_related_record = !is_linked_announcement_reference(frm);
	frm.toggle_display('linked_announcement_section', true);
	frm.toggle_display('linked_announcement_html', true);
	frm.toggle_display('references_section', show_related_record);
	frm.toggle_display('reference_type', show_related_record);
	frm.toggle_display('column_break_i1ra', show_related_record);
	frm.toggle_display('reference_name', show_related_record);
}

function sync_reference_field_lock(frm) {
	const is_linked_announcement = is_linked_announcement_reference(frm);
	const description = is_linked_announcement
		? __(
				'Managed by the Linked Announcement workflow below. Use that block to review the linked communication.'
			)
		: __(
				'Optional related Desk document. Org Communication links are managed automatically through Linked Announcement.'
			);

	frm.set_df_property('reference_type', 'read_only', is_linked_announcement ? 1 : 0);
	frm.set_df_property('reference_name', 'read_only', is_linked_announcement ? 1 : 0);
	frm.set_df_property('reference_type', 'description', description);
	frm.set_df_property('reference_name', 'description', description);
	frm.refresh_field('reference_type');
	frm.refresh_field('reference_name');
}

function render_linked_announcement_block(frm) {
	const wrapper = frm.get_field('linked_announcement_html')?.$wrapper;
	if (!wrapper?.length) return;

	bind_linked_announcement_actions(frm, wrapper);

	if (frm.is_new()) {
		frm.__linkedAnnouncementSummary = build_local_linked_announcement_summary(frm, {
			reason: __('Save the event before publishing a linked announcement.'),
		});
		render_linked_announcement_html(frm, frm.__linkedAnnouncementSummary);
		return;
	}

	if (frm.is_dirty()) {
		const dirty_summary = build_dirty_linked_announcement_summary(frm);
		frm.__linkedAnnouncementSummary = dirty_summary;
		render_linked_announcement_html(frm, dirty_summary);
		return;
	}

	const cache_key = [
		frm.doc.name || '',
		frm.doc.modified || '',
		frm.doc.reference_type || '',
		frm.doc.reference_name || '',
	].join(':');
	if (frm.__linkedAnnouncementSummary && frm.__linkedAnnouncementSummaryKey === cache_key) {
		render_linked_announcement_html(frm, frm.__linkedAnnouncementSummary);
		return;
	}

	wrapper.html(build_linked_announcement_loading_html());

	const request_token = `${Date.now()}:${Math.random()}`;
	frm.__linkedAnnouncementSummaryRequest = request_token;

	frappe
		.call({
			method: LINKED_ANNOUNCEMENT_SUMMARY_METHOD,
			args: { event: frm.doc.name },
		})
		.then(response => {
			if (frm.__linkedAnnouncementSummaryRequest !== request_token) return;
			const summary = normalize_linked_announcement_summary(response?.message, frm);
			frm.__linkedAnnouncementSummary = summary;
			frm.__linkedAnnouncementSummaryKey = cache_key;
			render_linked_announcement_html(frm, summary);
		})
		.catch(error => {
			if (frm.__linkedAnnouncementSummaryRequest !== request_token) return;
			const message =
				error?.message ||
				__('The linked announcement summary could not be loaded. Reload the form to retry.');
			const summary = {
				state: 'none',
				linked: false,
				announcement_name: null,
				title: null,
				status: null,
				portal_surface: null,
				audience_summary: null,
				can_open: false,
				can_publish: false,
				blocked_reason: message,
			};
			frm.__linkedAnnouncementSummary = summary;
			frm.__linkedAnnouncementSummaryKey = cache_key;
			render_linked_announcement_html(frm, summary);
		});
}

function build_dirty_linked_announcement_summary(frm) {
	const base_summary = normalize_linked_announcement_summary(frm.__linkedAnnouncementSummary, frm);

	if (is_linked_announcement_reference(frm)) {
		base_summary.linked = true;
		base_summary.state = base_summary.state === 'none' ? 'linked' : base_summary.state;
		base_summary.announcement_name =
			base_summary.announcement_name || frm.doc.reference_name || null;
		base_summary.title = base_summary.title || frm.doc.subject || frm.doc.reference_name || null;
		if (base_summary.state === 'linked') {
			base_summary.can_open = Boolean(base_summary.announcement_name);
		}
		base_summary.transient_note = __(
			'Unsaved event changes have not synced yet. Save to refresh the linked announcement summary.'
		);
		return base_summary;
	}

	return build_local_linked_announcement_summary(frm, {
		reason: __('Save your event changes before publishing a linked announcement.'),
	});
}

function build_local_linked_announcement_summary(frm, { reason }) {
	return {
		state: 'none',
		linked: false,
		announcement_name: null,
		title: null,
		status: null,
		portal_surface: null,
		audience_summary: null,
		can_open: false,
		can_publish: false,
		blocked_reason: reason,
	};
}

function normalize_linked_announcement_summary(raw_summary, frm) {
	const summary = raw_summary || {};
	return {
		state: summary.state || 'none',
		linked: Boolean(summary.linked),
		announcement_name: summary.announcement_name || null,
		title: summary.title || null,
		status: summary.status || null,
		portal_surface: summary.portal_surface || null,
		audience_summary: summary.audience_summary || null,
		can_open: Boolean(summary.can_open),
		can_publish: Boolean(summary.can_publish),
		blocked_reason: summary.blocked_reason || null,
		transient_note: summary.transient_note || null,
		subject_fallback: frm?.doc?.subject || null,
	};
}

function render_linked_announcement_html(frm, raw_summary) {
	const summary = normalize_linked_announcement_summary(raw_summary, frm);
	const wrapper = frm.get_field('linked_announcement_html')?.$wrapper;
	if (!wrapper?.length) return;

	const escape_html = frappe.utils.escape_html;
	const is_busy = Boolean(frm.__publishingLinkedAnnouncement);
	const can_publish = summary.state === 'none' && summary.can_publish && !is_busy;
	const can_open = summary.state === 'linked' && summary.can_open;
	const status_badge = render_status_badge(summary.status);
	const primary_title =
		summary.state === 'linked'
			? summary.title ||
				summary.subject_fallback ||
				summary.announcement_name ||
				__('Linked announcement')
			: summary.state === 'missing'
				? __('Linked announcement missing')
				: summary.state === 'permission_limited'
					? __('Linked announcement')
					: __('No linked announcement');

	const intro_copy =
		summary.state === 'linked'
			? __('Title and audience sync from this event. Edit the message in the announcement.')
			: summary.state === 'missing'
				? __(
						'This event still points to a linked announcement slot, but the announcement record could not be found.'
					)
				: summary.state === 'permission_limited'
					? __(
							'This event is linked to an announcement, but you do not have permission to open it from this form.'
						)
					: __(
							'This event is calendar-only right now. Publish an announcement if it should also appear in Communications.'
						);

	const audience_line = format_audience_line(summary.audience_summary);
	const surface_line = summary.portal_surface ? escape_html(summary.portal_surface) : '';
	const note_lines = [intro_copy];
	if (summary.transient_note) note_lines.push(summary.transient_note);

	const metadata = [];
	if (summary.announcement_name) {
		metadata.push(render_metadata_row(__('Announcement'), escape_html(summary.announcement_name)));
	}
	if (surface_line) {
		metadata.push(render_metadata_row(__('Surface'), surface_line));
	}
	if (audience_line) {
		metadata.push(render_metadata_row(__('Audience'), audience_line));
	}

	const warning_html = summary.blocked_reason
		? `<div style="margin-top:12px; padding:10px 12px; border-radius:8px; background:#fff7ed; color:#9a3412; font-size:12px;">
				${escape_html(summary.blocked_reason)}
			</div>`
		: '';

	const chips_html = render_audience_chips(summary.audience_summary);
	const notes_html = note_lines
		.filter(Boolean)
		.map(
			note => `<div class="text-muted small" style="margin-top:6px;">${escape_html(note)}</div>`
		)
		.join('');

	const action_buttons = [];
	if (
		summary.state === 'linked' ||
		summary.state === 'permission_limited' ||
		summary.state === 'missing'
	) {
		action_buttons.push(
			`<button type="button" class="btn btn-xs btn-default" data-linked-announcement-action="open" ${
				can_open ? '' : 'disabled'
			}>${escape_html(__('Open Announcement'))}</button>`
		);
	} else {
		action_buttons.push(
			`<button type="button" class="btn btn-xs btn-primary" data-linked-announcement-action="publish" ${
				can_publish ? '' : 'disabled'
			}>${escape_html(is_busy ? __('Publishing...') : __('Publish Announcement'))}</button>`
		);
	}

	wrapper.html(`
		<div style="border:1px solid #d1d8dd; border-radius:10px; background:#ffffff; padding:14px 16px;">
			<div style="display:flex; align-items:flex-start; justify-content:space-between; gap:12px; flex-wrap:wrap;">
				<div style="min-width:0;">
					<div class="text-muted small">${escape_html(__('Linked Announcement'))}</div>
					<div style="margin-top:4px; font-size:15px; font-weight:600; color:#0f172a;">
						${escape_html(primary_title)}
					</div>
					${notes_html}
				</div>
				${status_badge}
			</div>
			${metadata.length ? `<div style="margin-top:12px;">${metadata.join('')}</div>` : ''}
			${chips_html}
			${warning_html}
			<div style="margin-top:14px; display:flex; gap:8px; flex-wrap:wrap;">
				${action_buttons.join('')}
			</div>
		</div>
	`);
}

function render_metadata_row(label, value_html) {
	return `
		<div style="display:flex; gap:8px; margin-top:6px; font-size:12px;">
			<div class="text-muted" style="min-width:92px;">${frappe.utils.escape_html(label)}</div>
			<div style="color:#0f172a;">${value_html}</div>
		</div>
	`;
}

function render_status_badge(status) {
	if (!status) return '';
	const color = LINKED_ANNOUNCEMENT_STATUS_COLORS[status] || '#475569';
	return `
		<span style="display:inline-flex; align-items:center; gap:6px; border-radius:999px; background:${color}14; color:${color}; padding:4px 10px; font-size:12px; font-weight:600;">
			${frappe.utils.escape_html(status)}
		</span>
	`;
}

function render_audience_chips(audience_summary) {
	const chips = Array.isArray(audience_summary?.chips) ? audience_summary.chips : [];
	if (!chips.length) return '';

	const chip_html = chips
		.map(chip => {
			const tone = chip.type === 'scope' ? '#1d4ed8' : '#0f766e';
			return `<span style="display:inline-flex; align-items:center; border-radius:999px; background:${tone}14; color:${tone}; padding:4px 10px; font-size:12px; font-weight:600;">
				${frappe.utils.escape_html(chip.label || '')}
			</span>`;
		})
		.join('');

	return `<div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;">${chip_html}</div>`;
}

function format_audience_line(audience_summary) {
	const primary = audience_summary?.primary;
	if (!primary) return '';

	const recipients = Array.isArray(primary.recipients) ? primary.recipients.join(', ') : '';
	let scope = primary.scope_label || primary.scope_value || __('Whole audience');
	if (primary.scope_type === 'School' && Number(primary.include_descendants || 0)) {
		scope = __('{0} + descendants', [scope]);
	}

	let line = recipients ? __('{0} in {1}', [recipients, scope]) : scope;
	const audience_rows = Number(audience_summary?.meta?.audience_rows || 0);
	if (audience_rows > 1) {
		line = __('{0} (+{1} more audience rows)', [line, audience_rows - 1]);
	}
	return frappe.utils.escape_html(line);
}

function build_linked_announcement_loading_html() {
	return `
		<div style="border:1px solid #d1d8dd; border-radius:10px; background:#ffffff; padding:14px 16px;">
			<div class="text-muted small">${frappe.utils.escape_html(__('Linked Announcement'))}</div>
			<div style="margin-top:6px; font-size:13px; color:#64748b;">
				${frappe.utils.escape_html(__('Loading linked announcement details...'))}
			</div>
		</div>
	`;
}

function bind_linked_announcement_actions(frm, wrapper) {
	wrapper.off('.linkedAnnouncement');
	wrapper.on('click.linkedAnnouncement', '[data-linked-announcement-action]', event => {
		const action = event.currentTarget?.getAttribute('data-linked-announcement-action');
		if (action === 'open') {
			open_linked_announcement(frm);
			return;
		}
		if (action === 'publish') {
			publish_linked_announcement(frm);
		}
	});
}

function open_linked_announcement(frm) {
	const summary = normalize_linked_announcement_summary(frm.__linkedAnnouncementSummary, frm);
	if (!summary.announcement_name || !summary.can_open) return;
	frappe.set_route('Form', 'Org Communication', summary.announcement_name);
}

function publish_linked_announcement(frm) {
	const summary = normalize_linked_announcement_summary(frm.__linkedAnnouncementSummary, frm);
	if (!summary.can_publish || frm.is_new() || frm.is_dirty()) return;
	if (frm.__publishingLinkedAnnouncement) return;

	frm.__publishingLinkedAnnouncement = true;
	render_linked_announcement_block(frm);

	frappe
		.call({
			method: PUBLISH_LINKED_ANNOUNCEMENT_METHOD,
			args: { event: frm.doc.name },
		})
		.then(response => {
			frm.__publishingLinkedAnnouncement = false;
			const status = response?.message?.status;
			const message =
				status === 'already_linked'
					? __('A linked announcement already exists for this event.')
					: __('Linked announcement published.');
			frappe.show_alert({ message, indicator: 'green' });
			frm.reload_doc();
		})
		.catch(() => {
			frm.__publishingLinkedAnnouncement = false;
			render_linked_announcement_block(frm);
		});
}

// Show participants only for "Custom Users" audience rows
function toggle_participants_visibility(frm) {
	const rows = frm.doc.audience || [];
	const has_custom = rows.some(r => r.audience_type === 'Custom Users');
	frm.toggle_display('participants', has_custom);
}
