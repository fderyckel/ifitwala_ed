frappe.ui.form.on('Student', {
	refresh: function(frm) {
		frappe.dynamic_link = { doc: frm.doc, fieldname: "name", doctype: "Student" };

		if (!frm.doc.__islocal) {
			frm.trigger('setup_account_holder_filter');
		}

		if (frm.is_new()) {
			frm.disable_save();

			frm.set_intro(
				__(
					"<b>Direct Student creation is disabled.</b><br><br>" +
					"Students must be created via one of the following paths:<br>" +
					"1️⃣ <b>Admissions</b>: Promote a <i>Student Applicant</i><br>" +
					"2️⃣ <b>Migration / Import</b>: Use the Data Import tool (system-only)<br>" +
					"3️⃣ <b>System Scripts / API</b>: With explicit bypass flag<br><br>" +
					"If you are onboarding a new student, start from <b>Admissions</b>."
				),
				"orange"
			);
		}

		frm.trigger("render_contact_address_readonly");
		frm.trigger("refresh_crm_actions");
		frm.trigger("refresh_family_address_proposal");

		frm.trigger("setup_governed_image_upload");
		frm.trigger("setup_governed_drive_link");
		frm.trigger("setup_sibling_guardian_sync");
	},

    anchor_school: function(frm) {
        frm.trigger('setup_account_holder_filter');
    },

    setup_account_holder_filter: function(frm) {
        if (frm.doc.anchor_school) {
             frappe.call({
                method: "ifitwala_ed.accounting.account_holder_utils.get_school_organization",
                args: { school: frm.doc.anchor_school },
                callback: function(r) {
                    if (r.message) {
                        frm.set_query("account_holder", function() {
                            return {
                                filters: {
                                    organization: r.message
                                }
                            };
                        });
                    }
                }
             });
        }
    },

	render_contact_address_readonly: function(frm) {
		if (frm.is_new()) {
			frappe.contacts.clear_address_and_contact(frm);
			return;
		}

		frappe.contacts.render_address_and_contact(frm);
	},

	refresh_crm_actions: function(frm) {
		frm.remove_custom_button(__("Contact"), __("View"));
		frm.remove_custom_button(__("Address"), __("View"));
		frm.remove_custom_button(__("Addresses"), __("View"));

		if (frm.is_new()) {
			return;
		}

		frappe.call({
			method: "ifitwala_ed.students.doctype.student.student.get_student_crm_summary",
			args: { student_name: frm.doc.name },
			callback: function(r) {
				const summary = r.message || {};
				if (summary.contact) {
					frm.add_custom_button(
						__("Contact"),
						() => frappe.set_route("Form", "Contact", summary.contact),
						__("View")
					);
				}

				const addresses = Array.isArray(summary.addresses) ? summary.addresses : [];
				if (addresses.length === 1) {
					frm.add_custom_button(
						__("Address"),
						() => frappe.set_route("Form", "Address", addresses[0]),
						__("View")
					);
					return;
				}

				if (addresses.length > 1) {
					frm.add_custom_button(
						__("Addresses"),
						() => openAddressPickerDialog(addresses),
						__("View")
					);
				}
			}
		});
	},

	setup_sibling_guardian_sync: function(frm) {
		// Track siblings before save to detect new additions
		if (!frm.__siblings_before_save) {
			frm.__siblings_before_save = (frm.doc.siblings || []).map(s => s.student);
		}
	},

	refresh_family_address_proposal: function(frm) {
		frm.remove_custom_button(__("Review Family Address Links"), __("Actions"));
		if (frm.is_new()) {
			return;
		}

		frappe.call({
			method: "ifitwala_ed.students.doctype.student.student.get_family_address_link_proposal",
			args: { student_name: frm.doc.name },
			callback: function(r) {
				const proposal = r.message || {};
				if (!proposal.has_candidates || !proposal.address) {
					return;
				}

				frm.__family_address_proposal = proposal;
				frm.add_custom_button(
					__("Review Family Address Links"),
					() => frm.events.show_family_address_dialog(frm, proposal),
					__("Actions")
				);

				const promptKey = getFamilyAddressPromptKey(frm.doc.name, proposal.address);
				if (window.localStorage && window.localStorage.getItem(promptKey)) {
					return;
				}

				setTimeout(() => {
					if (frm.is_dirty() || frm.is_new()) {
						return;
					}
					frm.events.show_family_address_dialog(frm, proposal);
				}, 250);
			}
		});
	},

	show_family_address_dialog: function(frm, proposal) {
		if (!proposal?.address || !proposal.has_candidates) {
			return;
		}

		const promptKey = getFamilyAddressPromptKey(frm.doc.name, proposal.address);
		const guardianRows = Array.isArray(proposal.eligible_guardians) ? proposal.eligible_guardians : [];
		const siblingRows = Array.isArray(proposal.eligible_siblings) ? proposal.eligible_siblings : [];
		const skippedGuardians = Array.isArray(proposal.skipped_guardians) ? proposal.skipped_guardians : [];
		const skippedSiblings = Array.isArray(proposal.skipped_siblings) ? proposal.skipped_siblings : [];

		const fields = [
			{
				fieldtype: "HTML",
				fieldname: "context_html",
				options: buildFamilyAddressContextHtml(proposal),
			},
		];

		if (guardianRows.length) {
			fields.push({
				fieldtype: "MultiCheck",
				fieldname: "guardians",
				label: __("Guardians"),
				options: guardianRows.map((row) => ({
					label: row.relation
						? __("{0} ({1})", [row.guardian_name || row.guardian, row.relation])
						: (row.guardian_name || row.guardian),
					value: row.guardian,
					checked: 1,
				})),
			});
		}

		if (siblingRows.length) {
			fields.push({
				fieldtype: "MultiCheck",
				fieldname: "siblings",
				label: __("Siblings"),
				options: siblingRows.map((row) => ({
					label: row.sibling_name || row.student,
					value: row.student,
					checked: 1,
				})),
			});
		}

		if (skippedGuardians.length || skippedSiblings.length) {
			fields.push({
				fieldtype: "HTML",
				fieldname: "skipped_html",
				options: buildFamilyAddressSkippedHtml(skippedGuardians, skippedSiblings),
			});
		}

		const dialog = new frappe.ui.Dialog({
			title: __("Reuse Family Address"),
			fields,
			primary_action_label: __("Link Selected Records"),
			primary_action(values) {
				const guardians = normalizeMultiCheckValues(values.guardians);
				const siblings = normalizeMultiCheckValues(values.siblings);
				if (!guardians.length && !siblings.length) {
					frappe.show_alert({
						message: __("Select at least one family record to link."),
						indicator: "orange",
					});
					return;
				}

				frappe.call({
					method: "ifitwala_ed.students.doctype.student.student.link_family_address",
					args: {
						student_name: frm.doc.name,
						address_name: proposal.address,
						guardians,
						siblings,
					},
					freeze: true,
					freeze_message: __("Linking family address..."),
					callback: function(res) {
						const payload = res.message || {};
						const linkedTotal = cint(payload.guardians_count) + cint(payload.siblings_count);
						rememberFamilyAddressPrompt(promptKey);
						dialog.hide();
						frappe.show_alert({
							message: __("{0} family record(s) linked to Address {1}.", [linkedTotal, proposal.address]),
							indicator: "green",
						});
						frm.reload_doc();
					}
				});
			},
			secondary_action_label: __("Not Now"),
			secondary_action() {
				rememberFamilyAddressPrompt(promptKey);
				dialog.hide();
			},
		});

		dialog.show();
	},

	show_guardian_sync_dialog: function(frm, sibling_id, sibling_name) {
		if (!sibling_id) return;

		// Fetch sibling's guardians
		frappe.call({
			method: 'ifitwala_ed.students.doctype.student.student.get_student_guardians',
			args: { student_id: sibling_id },
			callback: function(r) {
				if (!r.message || r.message.length === 0) {
					frappe.show_alert({
						message: __('Sibling has no guardians to sync.'),
						indicator: 'orange'
					});
					return;
				}

				const sibling_guardians = r.message;
				const current_guardian_ids = (frm.doc.guardians || []).map(g => g.guardian);

				// Filter out guardians already present
				const new_guardians = sibling_guardians.filter(g => !current_guardian_ids.includes(g.guardian));

				if (new_guardians.length === 0) {
					frappe.show_alert({
						message: __('All guardians from this sibling are already added.'),
						indicator: 'green'
					});
					return;
				}

				// Build dialog content
				const guardian_list = new_guardians.map(g =>
					'<li><strong>' + frappe.utils.escape_html(g.guardian_name) + '</strong> (' + frappe.utils.escape_html(g.relation) + ')</li>'
				).join('');

				const d = new frappe.ui.Dialog({
					title: __('Sync Guardians from {0}', [sibling_name || sibling_id]),
					fields: [
						{
							fieldtype: 'HTML',
							fieldname: 'info',
							options: '<p>' + __('This sibling has the following guardians. Would you like to add them to this student?') + '</p><ul>' + guardian_list + '</ul>'
						}
					],
					primary_action_label: __('Add Guardians'),
					primary_action: function() {
						// Add guardians to current student
						new_guardians.forEach(g => {
							const row = frm.add_child('guardians');
							row.guardian = g.guardian;
							row.guardian_name = g.guardian_name;
							row.relation = g.relation;
							row.can_consent = g.can_consent;
							row.email = g.email;
							row.phone = g.phone;
						});
						frm.refresh_field('guardians');
						frappe.show_alert({
							message: __('{0} guardian(s) added.', [new_guardians.length]),
							indicator: 'green'
						});
						d.hide();
					},
					secondary_action_label: __('Skip'),
					secondary_action: function() {
						d.hide();
					}
				});
				d.show();
			}
		});
	},

	before_save: function(frm) {
		// Detect newly added siblings and show guardian sync dialog
		if (frm.__siblings_before_save) {
			const current_siblings = (frm.doc.siblings || []).map(s => s.student);
			const new_siblings = current_siblings.filter(s => !frm.__siblings_before_save.includes(s));

			if (new_siblings.length > 0 && !frm.__guardian_sync_shown) {
				frm.__guardian_sync_shown = true;
				// Get the first new sibling's details
				const sibling_row = frm.doc.siblings.find(s => s.student === new_siblings[0]);
				if (sibling_row) {
					// Delay to allow save to complete first
					setTimeout(() => {
						frm.events.show_guardian_sync_dialog(frm, sibling_row.student, sibling_row.sibling_name);
					}, 500);
				}
			}
		}
		frm.__siblings_before_save = (frm.doc.siblings || []).map(s => s.student);
	}
});

// Child table event handlers for siblings
frappe.ui.form.on('Student Sibling', {
	sibling_add: function(frm, cdt, cdn) {
		// Track that a new sibling was added
		if (!frm.__siblings_before_save) {
			frm.__siblings_before_save = (frm.doc.siblings || []).filter(s => s.name !== cdn).map(s => s.student);
		}
	},

	student: function(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.student && !row.__guardian_sync_checked) {
			row.__guardian_sync_checked = true;
			// Will be handled in before_save
		}
	},

	form_render: function(frm, cdt, cdn) {
		// Add sync button to each row
		const row = locals[cdt][cdn];
		const wrapper = frm.fields_dict.siblings.grid.grid_rows_by_docname[cdn]?.row;

		if (wrapper && row.student) {
			// Check if button already exists
			if (!wrapper.find('.btn-sync-guardians').length) {
				const $btn = $('<button class="btn btn-xs btn-default btn-sync-guardians" style="margin-left: 5px;">' +
					'<i class="fa fa-users"></i> ' + __('Sync Guardians') + '</button>');

				$btn.on('click', function(e) {
					e.preventDefault();
					e.stopPropagation();
					frm.events.show_guardian_sync_dialog(frm, row.student, row.sibling_name);
				});

				// Add button next to the row actions
				const $actions = wrapper.find('.row-check, .row-index');
				if ($actions.length) {
					$actions.after($btn);
				}
			}
		}
	}
});

frappe.ui.form.on("Student", {
	setup_governed_image_upload: function(frm) {
		const fieldname = "student_image";
		const openUploader = () => {
			if (frm.is_new()) {
				frappe.msgprint(__("Please save the Student before uploading an image."));
				return;
			}
			if (!frm.doc.anchor_school) {
				frappe.msgprint(__("Anchor School is required before uploading a student image."));
				return;
			}

			new frappe.ui.FileUploader({
				method: "ifitwala_ed.utilities.governed_uploads.upload_student_image",
				args: { student: frm.doc.name },
				doctype: "Student",
				docname: frm.doc.name,
				fieldname,
				is_private: 0,
				disable_private: true,
				allow_multiple: false,
				on_success(file_doc) {
					const payload = file_doc?.message
						|| (Array.isArray(file_doc) ? file_doc[0] : file_doc)
						|| (typeof file_doc === "string" ? { file_url: file_doc } : null);
					if (payload?.file_url) {
						frm.set_value(fieldname, payload.file_url);
						frm.refresh_field(fieldname);
					}
					frm.reload_doc();
				},
				on_error() {
					frappe.msgprint(__("Upload failed. Please try again."));
				},
			});
		};

		frm.set_df_property(fieldname, "read_only", 1);
		frm.set_df_property(
			fieldname,
			"description",
			__("Use the Upload Student Image action to attach a governed file.")
		);

		frm.remove_custom_button(__("Upload Student Image"), __("Actions"));
		frm.remove_custom_button(__("Upload Student Image"));
		frm.add_custom_button(
			__("Upload Student Image"),
			openUploader
		);

		const wrapper = frm.get_field(fieldname)?.$wrapper;
		if (wrapper?.length && !wrapper.find(".governed-upload-btn").length) {
			const $container = wrapper.find(".control-input").length
				? wrapper.find(".control-input")
				: wrapper;
			const $btn = $(
				`<button type="button" class="btn btn-xs btn-secondary governed-upload-btn">
          ${__("Upload Student Image")}
        </button>`
			);
			$btn.on("click", openUploader);
			$container.append($btn);
		}

		if (frm.is_new()) {
			return;
		}

		frm.call({
			method: "ifitwala_ed.utilities.governed_uploads.get_governed_status",
			args: {
				doctype: "Student",
				name: frm.doc.name,
				fieldname,
			},
		}).then((res) => {
			const governed = res?.message?.governed ? __("Governed ✅") : __("Governed ❌");
			const base = __("Use the Upload Student Image action to attach a governed file.");
			frm.set_df_property(fieldname, "description", `${base} ${governed}`);
		});
	},

	setup_governed_drive_link: function(frm) {
		const drive = window.ifitwala_ed && window.ifitwala_ed.drive;
		if (!drive || typeof drive.addOpenContextButton !== "function" || frm.is_new()) {
			return;
		}

		drive.addOpenContextButton(frm, {
			doctype: "Student",
			name: frm.doc.name,
			label: __("Open in Drive"),
			group: __("Actions"),
		});
	}
});

function cint(value) {
	return parseInt(value || 0, 10) || 0;
}

function normalizeMultiCheckValues(value) {
	if (!value) {
		return [];
	}
	if (Array.isArray(value)) {
		return value.filter(Boolean);
	}
	return Object.entries(value)
		.filter(([, checked]) => Boolean(checked))
		.map(([key]) => key);
}

function openAddressPickerDialog(addresses) {
	const options = (addresses || [])
		.map((addressName) => `
			<li>
				<a href="#" class="student-address-link" data-address="${frappe.utils.escape_html(addressName)}">
					${frappe.utils.escape_html(addressName)}
				</a>
			</li>
		`)
		.join("");

	const dialog = new frappe.ui.Dialog({
		title: __("Linked Addresses"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "addresses_html",
				options: `<p>${__("Select the Address record to open.")}</p><ul>${options}</ul>`,
			},
		],
	});

	dialog.show();
	dialog.$wrapper.on("click", ".student-address-link", function(event) {
		event.preventDefault();
		const addressName = $(event.currentTarget).data("address");
		if (addressName) {
			dialog.hide();
			frappe.set_route("Form", "Address", addressName);
		}
	});
}

function getFamilyAddressPromptKey(studentName, addressName) {
	return `ifitwala_ed:student-family-address:${studentName}:${addressName}`;
}

function rememberFamilyAddressPrompt(promptKey) {
	if (!window.localStorage || !promptKey) {
		return;
	}
	window.localStorage.setItem(promptKey, "1");
}

function buildFamilyAddressContextHtml(proposal) {
	const guardianCount = cint(proposal.eligible_guardians?.length);
	const siblingCount = cint(proposal.eligible_siblings?.length);
	const parts = [];
	if (guardianCount) {
		parts.push(__("{0} guardian(s)", [guardianCount]));
	}
	if (siblingCount) {
		parts.push(__("{0} sibling(s)", [siblingCount]));
	}
	const summary = parts.join(__(" and "));
	return `
		<p>
			${__("Address {0} is linked to this student.", [frappe.utils.escape_html(proposal.address)])}
		</p>
		<p>
			${__("You can reuse that same Address for {0} who do not already have an Address link.", [summary])}
		</p>
	`;
}

function buildFamilyAddressSkippedHtml(skippedGuardians, skippedSiblings) {
	const items = [];
	(skippedGuardians || []).forEach((row) => {
		items.push(`<li>${frappe.utils.escape_html(row.guardian_name || row.guardian)}: ${__("already has an Address link")}</li>`);
	});
	(skippedSiblings || []).forEach((row) => {
		items.push(`<li>${frappe.utils.escape_html(row.sibling_name || row.student)}: ${__("already has an Address link")}</li>`);
	});
	if (!items.length) {
		return "";
	}
	return `
		<div class="text-muted" style="margin-top: 12px;">
			<p>${__("Not included in this proposal:")}</p>
			<ul>${items.join("")}</ul>
		</div>
	`;
}
