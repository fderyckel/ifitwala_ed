// Copyright (c) 2024, fdR and contributors
// For license information, please see license.txt

// ifitwala_ed/admission/doctype/student_applicant/student_applicant.js

function blurActiveModalFocus() {
	const active = document.activeElement;
	if (!(active instanceof HTMLElement)) {
		return;
	}
	if (active.closest(".modal")) {
		active.blur();
	}
}

frappe.ui.form.on("Student Applicant", {

	refresh(frm) {
		frm.set_query("school", () => {
			if (!frm.doc.organization) {
				return { filters: { name: "" } };
			}
			return {
				query: "ifitwala_ed.admission.doctype.student_applicant.student_applicant.school_by_organization_query",
				filters: { organization: frm.doc.organization },
			};
		});
		frm.set_query("academic_year", () => {
			if (!frm.doc.school) {
				return { filters: { name: "" } };
			}
			return {
				query: "ifitwala_ed.admission.doctype.student_applicant.student_applicant.academic_year_intent_query",
				filters: { school: frm.doc.school },
			};
		});
		if (!frm.doc || frm.is_new()) {
			return;
		}
		frm.trigger("setup_governed_image_upload");
		render_review_sections(frm);
		add_decision_actions(frm);
		add_portal_invite_action(frm);
	},

	setup_governed_image_upload(frm) {
		const fieldname = "applicant_image";
		const openUploader = () => {
			if (frm.is_new()) {
				frappe.msgprint(__("Please save the Student Applicant before uploading an image."));
				return;
			}

			new frappe.ui.FileUploader({
				method: "ifitwala_ed.utilities.governed_uploads.upload_applicant_image",
				args: { student_applicant: frm.doc.name },
				doctype: "Student Applicant",
				docname: frm.doc.name,
				fieldname,
				is_private: 1,
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
			__("Use the Upload Applicant Image action to attach a governed file.")
		);

		frm.remove_custom_button(__("Upload Applicant Image"), __("Actions"));
		frm.remove_custom_button(__("Upload Applicant Image"));
		frm.add_custom_button(
			__("Upload Applicant Image"),
			openUploader
		);

		const wrapper = frm.get_field(fieldname)?.$wrapper;
		if (wrapper?.length && !wrapper.find(".governed-upload-btn").length) {
			const $container = wrapper.find(".control-input").length
				? wrapper.find(".control-input")
				: wrapper;
			const $btn = $(
				`<button type="button" class="btn btn-xs btn-secondary governed-upload-btn">
          ${__("Upload Applicant Image")}
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
				doctype: "Student Applicant",
				name: frm.doc.name,
				fieldname,
			},
		}).then((res) => {
			const governed = res?.message?.governed ? __("Governed ✅") : __("Governed ❌");
			const base = __("Use the Upload Applicant Image action to attach a governed file.");
			frm.set_df_property(fieldname, "description", `${base} ${governed}`);
		});
	},
});

const TERMINAL_PORTAL_INVITE_STATUSES = new Set(["Rejected", "Withdrawn", "Promoted"]);

function add_portal_invite_action(frm) {
	frm.remove_custom_button(__("Invite Applicant Portal"), __("Actions"));
	frm.remove_custom_button(__("Resend Portal Invite"), __("Actions"));
	frm.remove_custom_button(__("Invite Applicant Portal"));
	frm.remove_custom_button(__("Resend Portal Invite"));

	if (!frm.doc || frm.is_new()) {
		return;
	}

	const status = String(frm.doc.application_status || "").trim();
	if (TERMINAL_PORTAL_INVITE_STATUSES.has(status)) {
		return;
	}

	const hasLinkedUser = Boolean(String(frm.doc.applicant_user || "").trim());
	const label = hasLinkedUser ? __("Resend Portal Invite") : __("Invite Applicant Portal");
	frm.add_custom_button(label, () => prompt_portal_invite(frm), __("Actions"));
}

function prompt_portal_invite(frm) {
	const linkedEmail = String(frm.doc.applicant_user || "").trim().toLowerCase();
	const hasLinkedUser = Boolean(linkedEmail);

	frappe.call({
		method: "ifitwala_ed.api.admissions_portal.get_invite_email_options",
		args: {
			student_applicant: frm.doc.name,
		},
	})
		.then((res) => {
			const payload = res?.message || {};
			const emails = Array.isArray(payload.emails) ? payload.emails : [];
			const selectedEmail = String(payload.selected_email || "").trim().toLowerCase();

			const fields = [];
			if (emails.length) {
				fields.push({
					label: __("Contact Email"),
					fieldname: "selected_email",
					fieldtype: "Select",
					reqd: 0,
					options: emails.join("\n"),
					default: selectedEmail || emails[0],
					description: __("Select an existing Contact email."),
				});
			}

			fields.push({
				label: __("New Email"),
				fieldname: "new_email",
				fieldtype: "Data",
				options: "Email",
				reqd: !emails.length,
				description: emails.length
					? __("Optional: enter a new email to add to Contact and invite.")
					: __("Enter applicant email to create/link Contact and invite."),
			});

			frappe.prompt(
				fields,
				(values) => {
					const newEmail = String(values.new_email || "").trim().toLowerCase();
					const pickedEmail = String(values.selected_email || "").trim().toLowerCase();
					const email = newEmail || pickedEmail;
					if (!email) {
						frappe.msgprint(__("Please select or enter an applicant email."));
						return;
					}

					frappe.call({
						method: "ifitwala_ed.api.admissions_portal.invite_applicant",
						args: {
							student_applicant: frm.doc.name,
							email,
						},
						freeze: true,
						freeze_message: hasLinkedUser
							? __("Re-sending applicant portal invite...")
							: __("Inviting applicant to portal..."),
					})
						.then((inviteRes) => {
							const message = inviteRes?.message || {};
							const resent = Boolean(message.resent);
							const emailSent = message.email_sent !== false;
							frappe.show_alert({
								message: emailSent
									? (resent ? __("Portal invite email re-sent.") : __("Portal invite email sent."))
									: __("Portal access linked, but invite email could not be sent."),
								indicator: "green",
							});
							if (!emailSent) {
								frappe.msgprint(__("Applicant user and role were created/linked, but email sending failed. Ask family to use Forgot Password on /login or click Resend Portal Invite later."));
							}
							frm.reload_doc();
						})
						.catch((err) => {
							frappe.msgprint(err?.message || __("Unable to send applicant portal invite."));
						});
				},
				hasLinkedUser ? __("Resend Portal Invite") : __("Invite Applicant Portal"),
				hasLinkedUser ? __("Resend") : __("Invite")
			);
		})
		.catch((err) => {
			frappe.msgprint(err?.message || __("Unable to load applicant invite email options."));
		});
}

function render_review_sections(frm) {
	frm.call("get_readiness_snapshot")
		.then((res) => {
			const data = res && res.message;
			if (!data) {
				set_html(frm, "review_snapshot", render_empty("No readiness data."));
				return;
			}
			set_html(frm, "review_snapshot", render_snapshot(data));
			set_html(frm, "interviews_summary", render_interviews(data.interviews));
			set_html(frm, "health_summary", render_health(data.health));
			set_html(frm, "policies_summary", render_policies(data.policies));
			set_html(frm, "documents_summary", render_documents(data.documents));
		})
		.catch(() => {
			set_html(frm, "review_snapshot", render_empty("Unable to load review snapshot."));
		});
}

function set_html(frm, fieldname, html) {
	if (!frm.fields_dict[fieldname]) {
		return;
	}
	frm.fields_dict[fieldname].$wrapper.html(html);
}

function render_snapshot(data) {
	const ready = data.ready ? "Yes" : "No";
	const issues = data.issues || [];
	return [
		render_line("Ready for approval", escape_html(ready)),
		render_line("Readiness issues", render_list(issues)),
		render_line("Policies", render_ok_label(data.policies)),
		render_line("Documents", render_ok_label(data.documents)),
		render_line("Health", render_ok_label(data.health)),
		render_line("Interviews", render_ok_label(data.interviews)),
	].join("");
}

function render_interviews(interviews) {
	if (!interviews) {
		return render_empty("No interview data.");
	}
	const count = Number(interviews.count || 0);
	const items = Array.isArray(interviews.items) ? interviews.items : [];
	return [
		render_line("Interview count", escape_html(String(count))),
		render_line("Recent interviews", render_interview_links(items)),
	].join("");
}

function render_interview_links(items) {
	if (!items.length) {
		return escape_html("None");
	}

	const links = items
		.map((row) => {
			const name = String(row?.name || "").trim();
			if (!name) {
				return "";
			}
			const date = String(row?.interview_date || "").trim();
			const type = String(row?.interview_type || "").trim();
			const pieces = [name];
			if (date) {
				pieces.push(date);
			}
			if (type) {
				pieces.push(type);
			}
			const label = escape_html(pieces.join(" · "));
			const href = `/app/applicant-interview/${encodeURIComponent(name)}`;
			return `<a href="${href}">${label}</a>`;
		})
		.filter(Boolean);

	if (!links.length) {
		return escape_html("None");
	}
	return links.join(", ");
}

function render_health(health) {
	if (!health) {
		return render_empty("No health profile data.");
	}
	const label = map_health_status(health.status);
	return [
		render_line("Review status", escape_html(label)),
	].join("");
}

function render_policies(policies) {
	if (!policies) {
		return render_empty("No policy data.");
	}
	if (policies.ok) {
		return render_line("Status", "All required policies acknowledged.");
	}
	return render_line("Missing policies", render_list(policies.missing));
}

function render_documents(documents) {
	if (!documents) {
		return render_empty("No document data.");
	}
	if (documents.ok) {
		return render_line("Status", "All required documents approved.");
	}
	return [
		render_line("Missing", render_list(documents.missing)),
		render_line("Not approved", render_list(documents.unapproved)),
	].join("");
}

function render_ok_label(section) {
	if (!section) {
		return escape_html("Unknown");
	}
	return section.ok ? "OK" : "Needs Review";
}

function render_line(label, value) {
	return `<div><strong>${escape_html(label)}:</strong> ${value}</div>`;
}

function render_list(items) {
	if (!items || !items.length) {
		return escape_html("None");
	}
	return items.map((item) => escape_html(String(item))).join(", ");
}

function render_empty(message) {
	return `<div class='text-muted'>${escape_html(message)}</div>`;
}

function escape_html(value) {
	return frappe.utils.escape_html(value || "");
}

function map_health_status(status) {
	if (status === "complete") {
		return "Cleared";
	}
	if (status === "needs_follow_up") {
		return "Needs Follow-Up";
	}
	return "Pending";
}

function add_decision_actions(frm) {
	const status = frm.doc.application_status;
	["Start Review", "Approve", "Reject", "Promote", "Upgrade Identity"].forEach((label) =>
		frm.remove_custom_button(label)
	);

	if (status === "Submitted") {
		frm.add_custom_button("Start Review", () => {
			frappe.confirm("Move this applicant to Under Review?", () => {
				blurActiveModalFocus();
				frm.call("mark_under_review")
					.then(() => frm.reload_doc())
					.catch((err) => {
						frappe.msgprint(err.message || "Unable to move applicant to Under Review.");
					});
			});
		});
	}

	if (status === "Under Review") {
		frm.add_custom_button("Approve", () => {
			frappe.confirm("Approve this applicant?", () => {
				blurActiveModalFocus();
				frm.call("approve_application")
					.then(() => frm.reload_doc())
					.catch((err) => {
						frappe.msgprint(err.message || "Unable to approve applicant.");
					});
			});
		});

		frm.add_custom_button("Reject", () => {
			frappe.prompt(
				{
					label: "Rejection Reason",
					fieldname: "reason",
					fieldtype: "Small Text",
					reqd: 1,
				},
				(values) => {
					blurActiveModalFocus();
					frm.call("reject_application", { reason: values.reason })
						.then(() => frm.reload_doc())
						.catch((err) => {
							frappe.msgprint(err.message || "Unable to reject applicant.");
						});
				},
				"Reject Applicant",
				"Reject"
			);
		});
	}

	if (status === "Approved") {
		frm.add_custom_button("Promote", () => {
			frappe.confirm("Promote this applicant to Student?", () => {
				blurActiveModalFocus();
				frm.call("promote_to_student")
					.then(() => frm.reload_doc())
					.catch((err) => {
						frappe.msgprint(err.message || "Unable to promote applicant.");
					});
			});
		});
	}

	if (status === "Promoted") {
		frm.add_custom_button("Upgrade Identity", () => {
			frappe.confirm("Upgrade identity for this promoted applicant?", () => {
				blurActiveModalFocus();
				frm.call("upgrade_identity")
					.then(() => frm.reload_doc())
					.catch((err) => {
						frappe.msgprint(err.message || "Unable to upgrade identity.");
					});
			});
		});
	}
}
