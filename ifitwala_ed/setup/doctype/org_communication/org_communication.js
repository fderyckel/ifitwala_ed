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

		frm.trigger('setup_governed_attachment_upload');

		// Portal surface / Brief dates UX
		update_brief_date_reqd(frm);

		// Visibility info
		show_visibility_hint(frm);
		sync_context_section_visibility(frm);
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

	audiences_remove(frm) {
		setup_issuing_school_field(frm);
		frm.trigger('setup_governed_attachment_upload');
	},

	activity_student_group(frm) {
		sync_context_section_visibility(frm);
		frm.trigger('setup_governed_attachment_upload');
	},

	activity_program_offering(frm) {
		sync_context_section_visibility(frm);
	},

	activity_booking(frm) {
		sync_context_section_visibility(frm);
	},

	admission_context_doctype(frm) {
		sync_context_section_visibility(frm);
	},

	admission_context_name(frm) {
		sync_context_section_visibility(frm);
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
		sync_context_section_visibility(frm);

		if (frm.doc.communication_type === 'Class Announcement') {
			frappe.msgprint({
				message: __(
					'For Class Announcements, please add at least one Audience row targeting ' +
					'<strong>Students</strong> with a <strong>Student Group</strong>. ' +
					'Set Target Mode to <strong>Student Group</strong> and enable <strong>To Students</strong>.'
				),
				indicator: 'blue',
				title: __('Class Announcement Audience')
			});
		}
	},

	setup_governed_attachment_upload(frm) {
		const openUploader = async () => {
			try {
				if (frm.is_new() || frm.is_dirty()) {
					await frm.save();
				}
			} catch (error) {
				return;
			}

			if (!String(frm.doc.organization || '').trim()) {
				frappe.msgprint({
					title: __('Missing Organization'),
					indicator: 'orange',
					message: __('Set Organization on the communication before uploading governed attachments.')
				});
				return;
			}

			new frappe.ui.FileUploader({
				method: 'ifitwala_ed.api.org_communication_attachments.upload_org_communication_attachment',
				args: { org_communication: frm.doc.name },
				doctype: 'Org Communication',
				docname: frm.doc.name,
				is_private: 1,
				disable_private: true,
				allow_multiple: false,
				on_success() {
					frm.reload_doc();
				},
				on_error() {
					frappe.msgprint(__('Upload failed. Please try again.'));
				},
			});
		};

		const tableField = frm.get_field('attachments');
		const attachmentContextMode = resolve_attachment_context_mode(frm);
		const hasGovernedContext = attachmentContextMode !== 'missing-organization';

		if (tableField?.grid) {
			tableField.grid.update_docfield_property('file', 'read_only', 1);
			tableField.grid.update_docfield_property(
				'file',
				'description',
				__('Use the Upload Attachment action for governed files.')
			);

			tableField.grid.wrapper
				.find('.grid-custom-buttons .org-communication-upload-btn')
				.remove();

			const $gridButton = tableField.grid.add_custom_button(__('Upload Attachment'), openUploader);
			$gridButton.addClass('org-communication-upload-btn');
		}

		frm.set_df_property(
			'attachments',
			'description',
			!hasGovernedContext
				? __('Set Organization and save the communication before uploading governed files. External URLs can still be added manually.')
				: attachmentContextMode === 'class'
				? __('Use Upload Attachment for governed files. Class communications route attachments through the class context.')
				: attachmentContextMode === 'school'
				? __('Use Upload Attachment for governed files. School and team communications route attachments through the communication school context.')
				: __('Use Upload Attachment for governed files. Organization-wide communications route attachments through the organization context.')
		);

		frm.remove_custom_button(__('Upload Attachment'), __('Actions'));
		frm.remove_custom_button(__('Upload Attachment'));
		frm.add_custom_button(__('Upload Attachment'), openUploader, __('Actions'));
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

function has_organization_audience(frm) {
	return Boolean((frm.doc.audiences || []).some(row => (row.target_mode || '').trim() === 'Organization'));
}

function resolve_attachment_student_group(frm) {
	const activityStudentGroup = (frm.doc.activity_student_group || '').trim();
	if (activityStudentGroup) {
		return activityStudentGroup;
	}

	const audienceRows = frm.doc.audiences || [];
	const matchingRow = audienceRows.find(row =>
		(row.target_mode || '').trim() === 'Student Group' && (row.student_group || '').trim()
	);
	return (matchingRow?.student_group || '').trim();
}

function resolve_attachment_context_mode(frm) {
	if (!String(frm.doc.organization || '').trim()) {
		return 'missing-organization';
	}

	if (resolve_attachment_student_group(frm)) {
		return 'class';
	}

	if (String(frm.doc.school || '').trim()) {
		return 'school';
	}

	const audienceRows = frm.doc.audiences || [];
	const schoolRows = audienceRows.filter(row =>
		(row.target_mode || '').trim() === 'School Scope' && String(row.school || '').trim()
	);
	const uniqueSchools = new Set(schoolRows.map(row => String(row.school || '').trim()).filter(Boolean));
	if (uniqueSchools.size === 1) {
		return 'school';
	}

	const hasTeamContext = audienceRows.some(row =>
		(row.target_mode || '').trim() === 'Team' && String(row.team || '').trim()
	);
	if (hasTeamContext) {
		return 'school';
	}

	return 'organization';
}

function should_show_activity_context(frm) {
	return Boolean(
		(frm.doc.communication_type || '').trim() === 'Class Announcement' ||
		(frm.doc.activity_program_offering || '').trim() ||
		(frm.doc.activity_booking || '').trim() ||
		(frm.doc.activity_student_group || '').trim()
	);
}

function should_show_admission_context(frm) {
	return Boolean(
		(frm.doc.admission_context_doctype || '').trim() ||
		(frm.doc.admission_context_name || '').trim()
	);
}

function sync_context_section_visibility(frm) {
	const showActivityContext = should_show_activity_context(frm);
	const showAdmissionContext = should_show_admission_context(frm);

	frm.toggle_display(
		[
			'activity_context_section',
			'activity_program_offering',
			'activity_booking',
			'column_break_activity_context',
			'activity_student_group'
		],
		showActivityContext
	);

	frm.toggle_display(
		[
			'admission_context_section',
			'admission_context_doctype',
			'admission_context_name'
		],
		showAdmissionContext
	);
}

function setup_issuing_school_field(frm) {
	const ctx = frm._org_comm_ctx || {};
	const default_school = ctx.default_school || null;
	const default_organization = ctx.default_organization || null;
	const allowed_schools = ctx.allowed_schools || [];
	const allowed_organizations = ctx.allowed_organizations || [];
	const is_privileged = !!ctx.is_privileged;
	const can_select_school = !!ctx.can_select_school;
	const lock_to_default_school = !!ctx.lock_to_default_school;
	const needs_blank_school = has_organization_audience(frm);

	if (!frm.doc.organization && default_organization) {
		frm.set_value('organization', default_organization);
	}

	if (frm.fields_dict.organization) {
		frm.set_df_property('organization', 'read_only', 0);
		frm.set_df_property(
			'organization',
			'description',
			__('Organization is required and defaults from your user scope.')
		);

		if (allowed_organizations && allowed_organizations.length) {
			frm.set_query('organization', () => {
				return {
					filters: {
						name: ['in', allowed_organizations]
					}
				};
			});
		}
	}

	if (needs_blank_school) {
		if (frm.doc.school) {
			frm.set_value('school', '');
		}
		if (frm.fields_dict.school) {
			frm.set_df_property('school', 'read_only', 1);
			frm.set_df_property(
				'school',
				'description',
				__('Leave Issuing School blank because Organization audience rows are organization-level.')
			);
		}
		return;
	}

	if (lock_to_default_school) {
		// Non-privileged staff with default school: lock to default school
		if (default_school && frm.doc.school !== default_school) {
			frm.set_value('school', default_school);
		}
		if (frm.fields_dict.school) {
			frm.set_df_property('school', 'read_only', 1);
			frm.set_df_property(
				'school',
				'description',
				__('Issuing School is fixed to your default school when your school scope is locked.')
			);
		}
	} else if (can_select_school || is_privileged) {
		// Selectable mode:
		// - privileged roles (existing behavior)
		// - non-privileged users with org-scoped school selection (no default school)
		if (!frm.doc.school && default_school) {
			frm.set_value('school', default_school);
		}

		if (frm.fields_dict.school) {
			frm.set_df_property('school', 'read_only', 0);
			frm.set_df_property(
				'school',
				'description',
				is_privileged
					? __('Optional issuing school (within your scope). Leave blank for organization-level communication.')
					: __('Optional issuing school from your organization scope.')
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
	} else if (frm.fields_dict.school) {
		frm.set_df_property('school', 'read_only', 1);
		frm.set_df_property(
			'school',
			'description',
			__('No issuing school scope is configured. Use organization-level communication or ask admin to configure school scope.')
		);
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
		apply_recipient_defaults(frm, cdt, cdn, row);
		setup_issuing_school_field(frm);
		frm.trigger('setup_governed_attachment_upload');

		// If row.school is empty, inherit parent Issuing School for School Scope only
		if (row.target_mode === 'School Scope' && !row.school && frm.doc.school) {
			frappe.model.set_value(cdt, cdn, 'school', frm.doc.school);
		}
	},

	form_render(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		apply_audience_row_visibility(frm, cdt, cdn, row);
		apply_recipient_defaults(frm, cdt, cdn, row);
	},

	org_communication_audience_add(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.target_mode) {
			frappe.model.set_value(cdt, cdn, 'target_mode', 'School Scope');
			return;
		}
		apply_audience_row_visibility(frm, cdt, cdn, row);
		apply_recipient_defaults(frm, cdt, cdn, row);
		frm.trigger('setup_governed_attachment_upload');
	},

	student_group(frm) {
		frm.trigger('setup_governed_attachment_upload');
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

	toggle_grid_field(get_grid_field(gf, 'school'), show_school_scope);
	toggle_grid_field(get_grid_field(gf, 'include_descendants'), show_school_scope);
	toggle_grid_field(get_grid_field(gf, 'team'), show_team);
	toggle_grid_field(get_grid_field(gf, 'student_group'), show_student_group);

	update_recipient_toggle_state(gf, target_mode);

	toggle_grid_field(get_grid_field(gf, 'note'), true);
}

function update_recipient_toggle_state(gf, target_mode) {
	const allowed = get_allowed_recipient_fields(target_mode);
	const toggle_fields = ['to_staff', 'to_students', 'to_guardians'];

	toggle_fields.forEach(fieldname => {
		const field = get_grid_field(gf, fieldname);
		if (!field) return;

		toggle_grid_field(field, true);
		field.df.read_only = allowed.length ? !allowed.includes(fieldname) : 0;
		field.refresh && field.refresh();
	});
}

function get_grid_field(grid_form, fieldname) {
	if (!grid_form) return null;
	if (grid_form.get_field) {
		return grid_form.get_field(fieldname);
	}
	if (grid_form.fields_dict && grid_form.fields_dict[fieldname]) {
		return grid_form.fields_dict[fieldname];
	}
	return null;
}

function toggle_grid_field(field, show) {
	if (!field) return;
	if (field.toggle) {
		field.toggle(show);
	} else if (field.$wrapper || field.wrapper) {
		const $wrapper = field.$wrapper || $(field.wrapper);
		$wrapper && $wrapper.toggle(show);
	}
	if (field.df) {
		field.df.hidden = show ? 0 : 1;
	}
	field.refresh && field.refresh();
}

function get_allowed_recipient_fields(target_mode) {
	if (target_mode === 'Organization') {
		return ['to_staff'];
	}
	if (target_mode === 'Team') {
		return ['to_staff'];
	}
	if (target_mode === 'Student Group') {
		return ['to_staff', 'to_students', 'to_guardians'];
	}
	if (target_mode === 'School Scope') {
		return ['to_staff', 'to_students', 'to_guardians'];
	}
	return [];
}

function is_checked(value) {
	return value === 1 || value === '1' || value === true;
}

function apply_recipient_defaults(frm, cdt, cdn, row) {
	if (!row) return;

	const target_mode = (row.target_mode || '').trim();
	if (!target_mode) return;

	const allowed = get_allowed_recipient_fields(target_mode);
	const toggle_fields = ['to_staff', 'to_students', 'to_guardians'];

	const values = {
		to_staff: is_checked(row.to_staff),
		to_students: is_checked(row.to_students),
		to_guardians: is_checked(row.to_guardians)
	};

	toggle_fields.forEach(fieldname => {
		if (allowed.length && !allowed.includes(fieldname) && values[fieldname]) {
			values[fieldname] = false;
			frappe.model.set_value(cdt, cdn, fieldname, 0);
		}
	});

	if (target_mode === 'Team') {
		if (!values.to_staff) {
			values.to_staff = true;
			frappe.model.set_value(cdt, cdn, 'to_staff', 1);
		}
		return;
	}

	if (target_mode === 'Organization') {
		if (!values.to_staff) {
			values.to_staff = true;
			frappe.model.set_value(cdt, cdn, 'to_staff', 1);
		}
		return;
	}

	if (target_mode === 'Student Group') {
		const has_any = toggle_fields.some(fieldname => values[fieldname]);
		if (!has_any) {
			frappe.model.set_value(cdt, cdn, 'to_students', 1);
			frappe.model.set_value(cdt, cdn, 'to_guardians', 1);
			frappe.model.set_value(cdt, cdn, 'to_staff', 0);
		}
		return;
	}

	if (target_mode === 'School Scope') {
		if (toggle_fields.some(fieldname => values[fieldname])) return;
	}
}
