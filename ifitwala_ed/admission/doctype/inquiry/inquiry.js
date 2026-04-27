// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/admission/doctype/inquiry/inquiry.js

function blurActiveModalFocus() {
	const active = document.activeElement;
	if (!(active instanceof HTMLElement)) {
		return;
	}
	if (active.closest(".modal")) {
		active.blur();
	}
}

frappe.ui.form.on("Inquiry", {
	setup(frm) {
		frm.set_query('organization', () => ({
			query: 'ifitwala_ed.api.inquiry.inquiry_organization_link_query'
		}));

		frm.set_query('school', () => {
			const organization = String(frm.doc.organization || '').trim();
			if (!organization) {
				return {};
			}
			return {
				query: 'ifitwala_ed.admission.admission_utils.school_by_organization_scope_query',
				filters: { organization }
			};
		});
	},

	organization(frm) {
		if (!String(frm.doc.organization || '').trim()) {
			return;
		}
		if (!String(frm.doc.school || '').trim()) {
			return;
		}

		frm.set_value('school', null);
		frappe.show_alert({
			message: __('School was cleared. Please select a school in the selected organization scope.'),
			indicator: 'orange'
		});
	},

	refresh(frm) {
		frm.page.clear_actions_menu();
		frm.set_df_property(
			'assigned_to',
			'description',
			__('Change ownership through Assign/Reassign actions so scope checks, ToDos, and SLA timestamps stay consistent.')
		);

		const s = String(frm.doc.workflow_state || '').trim();
		const is_manager = frappe.user.has_role('Admission Manager');
		const is_officer = frappe.user.has_role('Admission Officer');
		const is_assigned_user = String(frm.doc.assigned_to || '').trim() === String(frappe.session.user || '').trim();
		const canonicalStates = new Set(['New', 'Assigned', 'Contacted', 'Qualified', 'Archived']);

		if (!canonicalStates.has(s)) {
			console.error(`Unknown Inquiry workflow_state: ${s}`);
			return;
		}

		// Assignment flows
		if (s === 'New' && is_manager) {
			frm.add_custom_button(__('Assign'), () => frm.trigger('assign'));
		}

		if (s === 'Assigned' && is_manager) {
			frm.add_custom_button(__('Reassign'), () => frm.trigger('reassign'));
		}

		if (s === 'Assigned' && (is_officer || is_manager || is_assigned_user)) {
			frm.add_custom_button(__('Mark Contacted'), () => frm.trigger('mark_contacted'));
		}

		if (s === 'Contacted' && is_officer) {
			frm.add_custom_button(__('Qualify'), () => frm.trigger('qualify'));
		}

		if (s !== 'Archived' && (is_manager || is_officer)) {
			frm.add_custom_button(__('Archive'), () => frm.trigger('archive'));
		}

		// --------------------------------------------------
		// Invite to Apply (Admissions boundary)
		// --------------------------------------------------
		// Only when inquiry is meaningful AND not archived
		if (
			(s === 'Qualified' || s === 'Contacted') &&
			(is_manager || is_officer)
		) {
			frm.add_custom_button(
				__('Invite to Apply'),
				() => frm.trigger('convert_to_applicant'),
				__('Admissions')
			);
		}

		// Contact creation (unchanged)
		if (!frm.doc.contact && frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Create Contact'), () => {
				frappe.call({
					doc: frm.doc,
					method: 'create_contact_from_inquiry',
					callback: (r) => {
						if (!r.exc) {
							frappe.show_alert({
								message: __('Contact Created: {0}', [r.message]),
								indicator: 'green'
							});
							frm.reload_doc();
						}
					}
				});
			});
		}
	},

	// --------------------------------------------------
	// Invite to Apply
	// --------------------------------------------------
	convert_to_applicant(frm) {
		let dialog = null;
		const schoolQuery = () => {
			const organization = String((dialog && dialog.get_value('organization')) || '').trim();
			if (!organization) {
				return { filters: { name: '' } };
			}
			return {
				query: 'ifitwala_ed.admission.admission_utils.school_by_organization_scope_query',
				filters: { organization }
			};
		};

		dialog = new frappe.ui.Dialog({
			title: __('Invite to Apply'),
			fields: [
				{
					label: __('Organization'),
					fieldname: 'organization',
					fieldtype: 'Link',
					options: 'Organization',
					reqd: 1,
					get_query: () => ({
						query: 'ifitwala_ed.api.inquiry.inquiry_organization_link_query'
					})
				},
				{
					label: __('School'),
					fieldname: 'school',
					fieldtype: 'Link',
					options: 'School',
					reqd: 1,
					get_query: schoolQuery
				}
			],
			primary_action_label: __('Invite'),
			primary_action: (values) => {
				const organization = String(values.organization || '').trim();
				const school = String(values.school || '').trim();

				if (!organization) {
					frappe.msgprint(__('Please select an Organization.'));
					return;
				}
				if (!school) {
					frappe.msgprint(__('Please select a School.'));
					return;
				}

				dialog.disable_primary_action();
				frappe.call({
					method: 'ifitwala_ed.admission.admission_utils.from_inquiry_invite',
					args: {
						inquiry_name: frm.doc.name,
						school,
						organization
					},
					freeze: true
				})
					.then((r) => {
						if (r && r.message) {
							frappe.show_alert(__('Applicant created'));
							blurActiveModalFocus();
							dialog.hide();
							frappe.set_route('Form', 'Student Applicant', r.message);
							return;
						}
						frappe.msgprint(__('Failed to invite applicant.'));
					})
					.catch((err) => {
						console.error(err);
						frappe.msgprint(__('Failed to invite applicant. Ensure School belongs to the selected Organization.'));
					})
					.then(() => {
						dialog.enable_primary_action();
					});
			}
		});

		const organizationField = dialog.get_field('organization');
		if (organizationField) {
			organizationField.df.onchange = () => {
				dialog.set_value('school', null);
			};
		}
		dialog.show();
	},

	// --------------------------------------------------
	// Existing handlers (UNCHANGED)
	// --------------------------------------------------

	assign(frm) {
		frappe.prompt(
			[
				{
					label: __('Assign To (Scoped Staff User)'),
					fieldname: 'assigned_to',
					fieldtype: 'Link',
					options: 'User',
					reqd: 1,
					get_query: () => ({
						query: "ifitwala_ed.admission.admission_utils.get_inquiry_assignees",
						filters: {
							organization: frm.doc.organization || '',
							school: frm.doc.school || ''
						}
					})
				}
			],
			(values) => {
				blurActiveModalFocus();
				frappe.call({
					method: 'ifitwala_ed.admission.admission_utils.assign_inquiry',
					args: {
						doctype: frm.doctype,
						docname: frm.docname,
						assigned_to: values.assigned_to
					},
					callback: (r) => {
						if (!r.exc) {
							const lane = r?.message?.assignment_lane || __('Unknown');
							frappe.msgprint(__('Inquiry assigned to {0} ({1} lane)', [values.assigned_to, lane]));
							frm.reload_doc();
						}
					}
				});
			},
			__('Assign Inquiry'),
			__('Assign')
		);
	},

	reassign(frm) {
		frappe.prompt(
			[
				{
					label: __('Reassign To (Scoped Staff User)'),
					fieldname: 'new_assigned_to',
					fieldtype: 'Link',
					options: 'User',
					reqd: 1,
					get_query: () => ({
						query: 'ifitwala_ed.admission.admission_utils.get_inquiry_assignees',
						filters: {
							organization: frm.doc.organization || '',
							school: frm.doc.school || ''
						}
					})
				}
			],
			(values) => {
				blurActiveModalFocus();
				frappe.call({
					method: 'ifitwala_ed.admission.admission_utils.reassign_inquiry',
					args: {
						doctype: frm.doctype,
						docname: frm.docname,
						new_assigned_to: values.new_assigned_to
					},
					callback: (r) => {
						if (!r.exc) {
							const lane = r?.message?.assignment_lane || __('Unknown');
							frappe.msgprint(__('Inquiry reassigned to {0} ({1} lane)', [values.new_assigned_to, lane]));
							frm.reload_doc();
						}
					}
				});
			},
			__('Reassign Inquiry'),
			__('Reassign')
		);
	},

	mark_contacted(frm) {
		frappe.confirm(
			__("Do you also want to mark the related task as completed?"),
			() => {
				blurActiveModalFocus();
				frappe.call({
					doc: frm.doc,
					method: "mark_contacted",
					args: { complete_todo: 1 },
					freeze: true,
					callback: function () {
						frappe.show_alert(__("Marked as contacted. Follow-up closed."));
						frm.reload_doc();
					}
				});
			},
			() => {
				blurActiveModalFocus();
				frappe.call({
					doc: frm.doc,
					method: "mark_contacted",
					args: { complete_todo: 0 },
					freeze: true,
					callback: function () {
						frappe.show_alert(__("Marked as contacted."));
						frm.reload_doc();
					}
				});
			}
		);
	},

	qualify(frm) {
		frappe.call({
			doc: frm.doc,
			method: "mark_qualified",
			freeze: true,
			callback: function () {
				frappe.show_alert(__("Marked as qualified."));
				frm.reload_doc();
			}
		});
	},

	archive(frm) {
		frappe.confirm(
			__("Archive this inquiry?"),
			() => {
				blurActiveModalFocus();
				frappe.call({
					doc: frm.doc,
					method: "archive",
					freeze: true,
					callback: function () {
						frappe.show_alert(__("Inquiry archived."));
						frm.reload_doc();
					}
				});
			}
		);
	}
});
