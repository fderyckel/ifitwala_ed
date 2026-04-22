// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/school_settings/doctype/school_event/school_event.js

frappe.ui.form.on('School Event', {
	onload(frm) {
		set_reference_type_query(frm);
	},

	refresh(frm) {
		add_reference_jump_button(frm);
		sync_reference_field_lock(frm);
		show_linked_announcement_hint(frm);
		toggle_participants_visibility(frm);
	},

	reference_type(frm) {
		sync_reference_field_lock(frm);
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

	const isAnnouncement = frm.doc.reference_type === 'Org Communication';
	const label = isAnnouncement ? __('Open Announcement') : __(frm.doc.reference_name);

	frm.add_custom_button(label, () => {
		frappe.set_route('Form', frm.doc.reference_type, frm.doc.reference_name);
	});
}

function show_linked_announcement_hint(frm) {
	if (frm.is_new() || frm.doc.reference_type !== 'Org Communication' || !frm.doc.reference_name)
		return;

	frappe.db
		.get_value('Org Communication', frm.doc.reference_name, ['status'])
		.then(response => {
			const status = response?.message?.status || response?.status || '';
			if (!status) return;
			const message = __(
				'Linked announcement: {0}. Event title and audience changes sync from this form, and cancelling the event archives the announcement.',
				[status]
			);
			if (frm.set_intro) {
				frm.set_intro(message, 'blue');
			}
		})
		.catch(() => {
			// Keep the form usable if the linked announcement can no longer be resolved.
		});
}

function sync_reference_field_lock(frm) {
	const isLinkedAnnouncement =
		frm.doc.reference_type === 'Org Communication' && Boolean(frm.doc.reference_name);
	const description = isLinkedAnnouncement
		? __(
				'Managed by the companion announcement workflow. Use Open Announcement to review or edit the linked communication.'
			)
		: __(
				'Optional reference to a related Desk document. Org Communication links are managed automatically.'
			);

	frm.set_df_property('reference_type', 'read_only', isLinkedAnnouncement ? 1 : 0);
	frm.set_df_property('reference_name', 'read_only', isLinkedAnnouncement ? 1 : 0);
	frm.set_df_property('reference_type', 'description', description);
	frm.set_df_property('reference_name', 'description', description);
	frm.refresh_field('reference_type');
	frm.refresh_field('reference_name');
}

// Show participants only for "Custom Users" audience rows
function toggle_participants_visibility(frm) {
	const rows = frm.doc.audience || [];
	const has_custom = rows.some(r => r.audience_type === 'Custom Users');
	frm.toggle_display('participants', has_custom);
}
