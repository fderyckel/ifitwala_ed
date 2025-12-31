// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/setup/doctype/org_communication/org_communication.js

frappe.ui.form.on('Org Communication', {
	refresh(frm) {
		// Fetch context once per form instance
		ensure_org_comm_context(frm).then(() => {
			setup_issuing_school_field(frm);
		});

		// Status-aware buttons
		if (!frm.is_new()) {
			frm.clear_custom_buttons();

			if (frm.doc.status === 'Draft') {
				frm.add_custom_button(__('Publish Now'), () => {
					publish_now(frm);
				}).addClass('btn-primary');

				frm.add_custom_button(__('Schedule…'), () => {
					open_schedule_dialog(frm);
				});
			}

			if (['Draft', 'Scheduled', 'Published'].includes(frm.doc.status)) {
				frm.add_custom_button(__('Archive'), () => {
					archive_communication(frm);
				});
			}
		}

		// Portal surface / Brief dates UX
		update_brief_date_reqd(frm);

		// Visibility info
		show_visibility_hint(frm);
	},

	portal_surface(frm) {
		update_brief_date_reqd(frm);
	},

	brief_start_date(frm) {
		normalize_brief_dates(frm);
	},

	brief_end_date(frm) {
		normalize_brief_dates(frm);
	},

	status(frm) {
		if (frm.doc.status === 'Scheduled' && !frm.doc.publish_from) {
			frappe.msgprint({
				message: __('Scheduled communications should have a "Publish From" date/time.'),
				indicator: 'orange'
			});
		}
		if (frm.doc.status === 'Published' && !frm.doc.publish_from) {
			frappe.show_alert({
				message: __('This communication will publish immediately (no "Publish From" set).'),
				indicator: 'blue'
			});
		}
	},

	communication_type(frm) {
		if (frm.doc.communication_type === 'Class Announcement') {
			frappe.msgprint({
				message: __(
					'For Class Announcements, please add at least one Audience row targeting ' +
					'<strong>Students</strong> with a <strong>Student Group</strong>. ' +
					'Set Target Mode to <strong>Student Group</strong> and include Students in Recipients.'
				),
				indicator: 'blue',
				title: __('Class Announcement Audience')
			});
		}
	}
});

// ----------------------------------------------------------
// Issuing School behaviour (parent.school)
// ----------------------------------------------------------

function ensure_org_comm_context(frm) {
	if (frm._org_comm_ctx) {
		return Promise.resolve(frm._org_comm_ctx);
	}

	return frappe.call({
		method: 'ifitwala_ed.setup.doctype.org_communication.org_communication.get_org_communication_context',
		args: {},
	}).then(r => {
		frm._org_comm_ctx = r.message || {};
		return frm._org_comm_ctx;
	});
}

function setup_issuing_school_field(frm) {
	const ctx = frm._org_comm_ctx || {};
	const default_school = ctx.default_school || null;
	const allowed_schools = ctx.allowed_schools || [];
	const is_privileged = !!ctx.is_privileged;

	// Organization is controlled server-side from School
	if (frm.fields_dict.organization) {
		frm.set_df_property('organization', 'read_only', 1);
	}

	if (!is_privileged) {
		// Non-privileged staff: Issuing School = default school, read-only
		if (default_school && frm.doc.school !== default_school) {
			frm.set_value('school', default_school);
		}
		if (frm.fields_dict.school) {
			frm.set_df_property('school', 'read_only', 1);
			frm.set_df_property(
				'school',
				'description',
				__('Issuing School is fixed to your default school.')
			);
		}
	} else {
		// Privileged roles: can choose Issuing School within their tree
		if (!frm.doc.school && default_school) {
			frm.set_value('school', default_school);
		}

		if (frm.fields_dict.school) {
			frm.set_df_property('school', 'read_only', 0);
			frm.set_df_property(
				'school',
				'description',
				__('Choose the school issuing this communication (within your scope).')
			);

			if (allowed_schools && allowed_schools.length) {
				frm.set_query('school', () => {
					return {
						filters: {
							name: ['in', allowed_schools]
						}
					};
				});
			}
		}
	}
}

// ----------------------------------------------------------
// Brief / visibility helpers
// ----------------------------------------------------------

function update_brief_date_reqd(frm) {
	const surface = (frm.doc.portal_surface || '').trim();
	const needs_brief = ['Morning Brief', 'Everywhere'].includes(surface);

	if (frm.fields_dict.brief_start_date) {
		frm.set_df_property('brief_start_date', 'reqd', needs_brief ? 1 : 0);
	}
}

function normalize_brief_dates(frm) {
	const start = frm.doc.brief_start_date;
	const end = frm.doc.brief_end_date;

	if (start && !end) {
		frm.set_value('brief_end_date', start);
		return;
	}

	if (start && end && end < start) {
		frappe.msgprint({
			message: __('Brief End Date cannot be before Brief Start Date. It has been reset.'),
			indicator: 'red'
		});
		frm.set_value('brief_end_date', start);
	}
}

function show_visibility_hint(frm) {
	const parts = [];

	if (frm.doc.publish_from) {
		parts.push(__('from {0}', [frappe.datetime.str_to_user(frm.doc.publish_from)]));
	}
	if (frm.doc.publish_to) {
		parts.push(__('until {0}', [frappe.datetime.str_to_user(frm.doc.publish_to)]));
	}

	let msg = '';
	if (parts.length) {
		msg = __('Visible {0}', [parts.join(' ')]);
	} else {
		msg = __('No publish window set. Visibility will depend on its status and audience.');
	}

	// set_intro was removed from frappe.utils in newer versions; prefer frm.set_intro if available
	if (frm.set_intro) {
		frm.set_intro(msg);
	} else if (frm.dashboard && frm.dashboard.set_headline) {
		// Fallback: show in the form headline
		frm.dashboard.clear_headline && frm.dashboard.clear_headline();
		frm.dashboard.set_headline(msg);
	} else {
		// Last resort: console for debugging
		console.warn('Visibility hint:', msg);
	}
}

// ----------------------------------------------------------
// Status helpers
// ----------------------------------------------------------

function publish_now(frm) {
	if (frm.is_dirty()) {
		frm.save().then(() => {
			set_published(frm);
		});
	} else {
		set_published(frm);
	}
}

function set_published(frm) {
	frm.set_value('status', 'Published');
	frm.save().then(() => {
		frappe.show_alert({
			message: __('Communication published.'),
			indicator: 'green'
		});
	});
}

function open_schedule_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __('Schedule Communication'),
		fields: [
			{
				fieldname: 'publish_from',
				fieldtype: 'Datetime',
				label: __('Publish From'),
				reqd: 1,
				default: frm.doc.publish_from || frappe.datetime.now_datetime()
			}
		],
		primary_action_label: __('Schedule'),
		primary_action(values) {
			d.hide();
			frm.set_value('publish_from', values.publish_from);
			frm.set_value('status', 'Scheduled');
			frm.save().then(() => {
				frappe.show_alert({
					message: __('Communication scheduled.'),
					indicator: 'green'
				});
			});
		}
	});

	d.show();
}

function archive_communication(frm) {
	frappe.confirm(
		__('Archive this communication? It will no longer appear in normal views but remain in the system.'),
		() => {
			frm.set_value('status', 'Archived');
			frm.save().then(() => {
				frappe.show_alert({
					message: __('Communication archived.'),
					indicator: 'orange'
				});
			});
		}
	);
}

// ----------------------------------------------------------
// Child table: Org Communication Audience
// ----------------------------------------------------------

frappe.ui.form.on('Org Communication Audience', {
	target_mode(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		apply_audience_row_visibility(frm, cdt, cdn, row);

		// If row.school is empty, inherit parent Issuing School for School Scope only
		if (row.target_mode === 'School Scope' && !row.school && frm.doc.school) {
			frappe.model.set_value(cdt, cdn, 'school', frm.doc.school);
		}
	},

	form_render(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		apply_audience_row_visibility(frm, cdt, cdn, row);
	},

	org_communication_audience_add(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		apply_audience_row_visibility(frm, cdt, cdn, row);
	}
});

function apply_audience_row_visibility(frm, cdt, cdn, row) {
	const target_mode = (row.target_mode || '').trim();
	const grid_row = frm.fields_dict.audiences.grid.get_row(cdn);
	if (!grid_row || !grid_row.grid_form) return;

	const gf = grid_row.grid_form;

	const show_school_scope = target_mode === 'School Scope';
	const show_team = target_mode === 'Team';
	const show_student_group = target_mode === 'Student Group';

	if (gf.get_field('school')) {
		gf.get_field('school').toggle(show_school_scope);
	}
	if (gf.get_field('include_descendants')) {
		gf.get_field('include_descendants').toggle(show_school_scope);
	}
	if (gf.get_field('team')) {
		gf.get_field('team').toggle(show_team);
	}
	if (gf.get_field('student_group')) {
		gf.get_field('student_group').toggle(show_student_group);
	}
	if (gf.get_field('recipients')) {
		gf.get_field('recipients').toggle(true);
	}
	if (gf.get_field('note')) {
		gf.get_field('note').toggle(true);
	}
}
