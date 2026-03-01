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
		add_recommendation_actions(frm);
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

const TERMINAL_RECOMMENDATION_STATUSES = new Set(["Rejected", "Withdrawn", "Promoted"]);

function add_recommendation_actions(frm) {
	frm.remove_custom_button(__("Request Recommendation"), __("Actions"));
	frm.remove_custom_button(__("Manage Recommendation Requests"), __("Actions"));
	frm.remove_custom_button(__("Request Recommendation"));
	frm.remove_custom_button(__("Manage Recommendation Requests"));

	if (!frm.doc || frm.is_new()) {
		return;
	}

	const status = String(frm.doc.application_status || "").trim();
	if (TERMINAL_RECOMMENDATION_STATUSES.has(status)) {
		return;
	}

	frm.add_custom_button(__("Request Recommendation"), () => {
		prompt_create_recommendation_request(frm);
	}, __("Actions"));

	frm.add_custom_button(__("Manage Recommendation Requests"), () => {
		open_recommendation_requests_dialog(frm);
	}, __("Actions"));
}

function prompt_create_recommendation_request(frm) {
	frappe.call({
		method: "ifitwala_ed.api.recommendation_intake.list_recommendation_templates",
		args: {
			student_applicant: frm.doc.name,
		},
	})
		.then((res) => {
			const templates = Array.isArray(res?.message?.templates) ? res.message.templates : [];
			if (!templates.length) {
				frappe.msgprint(__("No active recommendation template is configured for this applicant scope."));
				return;
			}

			const templateOptions = templates.map((row) => String(row?.name || "").trim()).filter(Boolean);
			const byName = {};
			templates.forEach((row) => {
				const key = String(row?.name || "").trim();
				if (key) {
					byName[key] = row;
				}
			});

			frappe.prompt(
				[
					{
						label: __("Recommendation Template"),
						fieldname: "recommendation_template",
						fieldtype: "Select",
						options: templateOptions.join("\n"),
						default: templateOptions[0],
						reqd: 1,
					},
					{
						label: __("Recommender Name"),
						fieldname: "recommender_name",
						fieldtype: "Data",
						reqd: 1,
					},
					{
						label: __("Recommender Email"),
						fieldname: "recommender_email",
						fieldtype: "Data",
						options: "Email",
						reqd: 1,
					},
					{
						label: __("Relationship to Applicant"),
						fieldname: "recommender_relationship",
						fieldtype: "Data",
					},
					{
						label: __("Item Label"),
						fieldname: "item_label",
						fieldtype: "Data",
						description: __("Optional label shown in Applicant Document item slot."),
					},
					{
						label: __("Expires In (days)"),
						fieldname: "expires_in_days",
						fieldtype: "Int",
						default: 14,
						reqd: 1,
					},
					{
						label: __("Send Email Now"),
						fieldname: "send_email",
						fieldtype: "Check",
						default: 1,
					},
				],
				(values) => {
					const templateName = String(values.recommendation_template || "").trim();
					const templateMeta = byName[templateName] || {};
					const recommenderEmail = String(values.recommender_email || "").trim();
					if (!templateName) {
						frappe.msgprint(__("Please select a recommendation template."));
						return;
					}
					if (!recommenderEmail) {
						frappe.msgprint(__("Recommender Email is required."));
						return;
					}
					frappe.call({
						method: "ifitwala_ed.api.recommendation_intake.create_recommendation_request",
						args: {
							student_applicant: frm.doc.name,
							recommendation_template: templateName,
							recommender_name: String(values.recommender_name || "").trim(),
							recommender_email: recommenderEmail,
							recommender_relationship: String(values.recommender_relationship || "").trim(),
							item_label: String(values.item_label || "").trim(),
							expires_in_days: Number(values.expires_in_days || 14),
							send_email: values.send_email ? 1 : 0,
							client_request_id: `${Date.now()}_${Math.random().toString(16).slice(2, 14)}`,
						},
						freeze: true,
						freeze_message: __("Creating recommendation request..."),
					})
						.then((response) => {
							const payload = response?.message || {};
							const intakeUrl = String(payload.intake_url || "").trim();
							const emailSent = payload.email_sent !== false;
							const parts = [
								emailSent
									? __("Recommendation request created and email sent.")
									: __("Recommendation request created, but email could not be sent."),
							];
							const templateLabel = String(templateMeta.template_name || templateName);
							parts.push(__("Template: {0}").replace("{0}", templateLabel));
							if (intakeUrl) {
								const safeUrl = frappe.utils.escape_html(intakeUrl);
								parts.push(
									`${__("Intake URL")}: <a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${safeUrl}</a>`
								);
							}
							frappe.msgprint({
								title: __("Recommendation Request Created"),
								message: `<div>${parts.join("<br>")}</div>`,
								indicator: emailSent ? "green" : "orange",
							});
							render_review_sections(frm);
						})
						.catch((error) => {
							frappe.msgprint(get_error_message(error, __("Unable to create recommendation request.")));
						});
				},
				__("Request Recommendation"),
				__("Create")
			);
		})
		.catch((error) => {
			frappe.msgprint(get_error_message(error, __("Unable to load recommendation templates.")));
		});
}

function render_recommendation_requests_table(payload) {
	const rows = Array.isArray(payload?.requests) ? payload.requests : [];
	const summary = payload?.summary || {};
	const counts = summary?.counts || {};

	const summaryText = [
		__("Submitted: {0}").replace("{0}", String(counts.Submitted || 0)),
		__("Sent: {0}").replace("{0}", String(counts.Sent || 0)),
		__("Opened: {0}").replace("{0}", String(counts.Opened || 0)),
		__("Expired: {0}").replace("{0}", String(counts.Expired || 0)),
		__("Revoked: {0}").replace("{0}", String(counts.Revoked || 0)),
	].join(" · ");

	if (!rows.length) {
		return `
			<div style="margin-bottom: 10px;">${escape_html(summaryText)}</div>
			<div class="text-muted">${escape_html("No recommendation requests yet.")}</div>
		`;
	}

	const body = rows.map((row) => {
		const requestName = String(row?.name || "").trim();
		const status = String(row?.request_status || "").trim() || "Sent";
		const canResend = ["Sent", "Opened", "Expired"].includes(status);
		const canRevoke = ["Sent", "Opened"].includes(status);
		return `
			<tr>
				<td>${escape_html(String(row?.template_name || row?.recommendation_template || "Template"))}</td>
				<td>${escape_html(String(row?.recommender_name || "—"))}</td>
				<td>${escape_html(String(row?.recommender_email || "—"))}</td>
				<td>${escape_html(status)}</td>
				<td>${escape_html(format_datetime(row?.sent_on))}</td>
				<td>${escape_html(format_datetime(row?.expires_on))}</td>
				<td>
					${canResend ? `<button type="button" class="btn btn-xs btn-default recommendation-action-btn" data-action="resend" data-request="${escape_html(requestName)}">${escape_html("Resend")}</button>` : ""}
					${canRevoke ? `<button type="button" class="btn btn-xs btn-default recommendation-action-btn" data-action="revoke" data-request="${escape_html(requestName)}" style="margin-left: 6px;">${escape_html("Revoke")}</button>` : ""}
				</td>
			</tr>
		`;
	}).join("");

	return `
		<div style="margin-bottom: 10px;">${escape_html(summaryText)}</div>
		<div class="table-responsive">
			<table class="table table-bordered table-sm" style="margin-bottom: 0;">
				<thead>
					<tr>
						<th>Template</th>
						<th>Recommender</th>
						<th>Email</th>
						<th>Status</th>
						<th>Sent On</th>
						<th>Expires On</th>
						<th>Actions</th>
					</tr>
				</thead>
				<tbody>${body}</tbody>
			</table>
		</div>
	`;
}

function open_recommendation_requests_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Recommendation Requests"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "body",
			},
		],
		primary_action_label: __("Close"),
		primary_action() {
			dialog.hide();
		},
	});

	const loadRows = () => {
		dialog.fields_dict.body.$wrapper.html(`<div class="text-muted">${escape_html("Loading recommendation requests...")}</div>`);
		return frappe.call({
			method: "ifitwala_ed.api.recommendation_intake.list_recommendation_requests",
			args: { student_applicant: frm.doc.name },
		}).then((res) => {
			const payload = res?.message || {};
			dialog.fields_dict.body.$wrapper.html(render_recommendation_requests_table(payload));
		}).catch((error) => {
			dialog.fields_dict.body.$wrapper.html(
				`<div class="text-danger">${escape_html(get_error_message(error, __("Unable to load recommendation requests.")))}</div>`
			);
		});
	};

	dialog.$wrapper.on("click", ".recommendation-action-btn", (event) => {
		const target = event.currentTarget;
		if (!(target instanceof HTMLElement)) {
			return;
		}
		const action = String(target.getAttribute("data-action") || "").trim();
		const requestName = String(target.getAttribute("data-request") || "").trim();
		if (!action || !requestName) {
			return;
		}
		if (action === "resend") {
			frappe.call({
				method: "ifitwala_ed.api.recommendation_intake.resend_recommendation_request",
				args: {
					recommendation_request: requestName,
				},
				freeze: true,
				freeze_message: __("Resending recommendation request..."),
			})
				.then((res) => {
					const payload = res?.message || {};
					const intakeUrl = String(payload.intake_url || "").trim();
					const safeUrl = intakeUrl ? frappe.utils.escape_html(intakeUrl) : "";
					frappe.msgprint({
						title: __("Recommendation Request Re-sent"),
						message: intakeUrl
							? `<div>${__("A new recommendation link was issued.")}<br>${__("Intake URL")}: <a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${safeUrl}</a></div>`
							: __("A new recommendation link was issued."),
						indicator: "green",
					});
					loadRows();
					render_review_sections(frm);
				})
				.catch((error) => {
					frappe.msgprint(get_error_message(error, __("Unable to resend recommendation request.")));
				});
			return;
		}

		if (action === "revoke") {
			frappe.confirm(__("Revoke this recommendation request?"), () => {
				frappe.call({
					method: "ifitwala_ed.api.recommendation_intake.revoke_recommendation_request",
					args: {
						recommendation_request: requestName,
					},
					freeze: true,
					freeze_message: __("Revoking recommendation request..."),
				})
					.then(() => {
						frappe.show_alert({ message: __("Recommendation request revoked."), indicator: "orange" });
						loadRows();
						render_review_sections(frm);
					})
					.catch((error) => {
						frappe.msgprint(get_error_message(error, __("Unable to revoke recommendation request.")));
					});
			});
		}
	});

	dialog.show();
	loadRows();
}

function get_error_message(error, fallbackMessage) {
	const fallback = String(fallbackMessage || "Unexpected error.");
	if (!error) {
		return fallback;
	}
	if (typeof error.message === "string" && error.message.trim()) {
		return error.message;
	}
	const serverMessages = error?._server_messages;
	if (Array.isArray(serverMessages) && serverMessages.length) {
		try {
			const first = JSON.parse(serverMessages[0]);
			if (first && typeof first.message === "string" && first.message.trim()) {
				return first.message;
			}
		} catch (_jsonError) {
			return fallback;
		}
	}
	return fallback;
}

function render_review_sections(frm) {
	frm.call("get_readiness_snapshot")
		.then((res) => {
			const data = res && res.message;
			if (!data) {
				set_html(frm, "review_snapshot", render_empty("No readiness data."));
				set_html(frm, "review_assignments_summary", render_empty("No review assignment decisions yet."));
				return;
			}
			set_html(frm, "review_snapshot", render_snapshot(data));
			set_html(frm, "review_assignments_summary", render_review_assignments(data.review_assignments));
			set_html(frm, "interviews_summary", render_interviews(data.interviews));
			set_html(frm, "health_summary", render_health(data.health));
			set_html(frm, "policies_summary", render_policies(data.policies));
			set_html(frm, "documents_summary", render_documents(data.documents));
		})
		.catch(() => {
			set_html(frm, "review_snapshot", render_empty("Unable to load review snapshot."));
			set_html(frm, "review_assignments_summary", render_empty("Unable to load review assignment summary."));
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
		render_line("Profile", render_ok_label(data.profile)),
		render_line("Policies", render_ok_label(data.policies)),
		render_line("Documents", render_ok_label(data.documents)),
		render_line("Recommendations", render_ok_label(data.recommendations)),
		render_line("Health", render_ok_label(data.health)),
		render_line("Interviews", render_ok_label(data.interviews)),
	].join("");
}

function render_review_assignments(summary) {
	const groups = [
		{ key: "Applicant Document", label: "Documents" },
		{ key: "Applicant Health Profile", label: "Health" },
		{ key: "Student Applicant", label: "Overall Application" },
	];

	const sections = groups
		.map((group) => {
			const rows = Array.isArray(summary?.[group.key]) ? summary[group.key] : [];
			const body = rows.length
				? rows
					.map((row) => `
						<tr>
							<td>${escape_html(String(row?.target_label || row?.target_name || "Item"))}</td>
							<td>${escape_html(String(row?.reviewer || "—"))}</td>
							<td>${escape_html(String(row?.decision || "—"))}</td>
							<td>${escape_html(format_datetime(row?.decided_on))}</td>
							<td>${escape_html(String(row?.notes || "—"))}</td>
						</tr>
					`)
					.join("")
				: `
					<tr>
						<td colspan="5" class="text-muted">No completed reviews.</td>
					</tr>
				`;

			return `
				<div style="margin-bottom: 12px;">
					<div style="font-weight: 600; margin-bottom: 6px;">${escape_html(group.label)}</div>
					<div class="table-responsive">
						<table class="table table-bordered table-sm" style="margin-bottom: 0;">
							<thead>
								<tr>
									<th>Target</th>
									<th>Reviewer</th>
									<th>Decision</th>
									<th>Decided On</th>
									<th>Notes</th>
								</tr>
							</thead>
							<tbody>${body}</tbody>
						</table>
					</div>
				</div>
			`;
		})
		.join("");

	return sections || render_empty("No review assignment decisions yet.");
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
			const href = `/desk/applicant-interview/${encodeURIComponent(name)}`;
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
	const reviewStatus = map_health_status(health.status);
	const reviewTone = health.status === "complete" ? "green" : health.status === "needs_follow_up" ? "red" : "amber";
	const declarationTone = health.declared_complete ? "green" : "amber";
	const profileLink = health.profile_name
			? render_text_link(
				`/desk/applicant-health-profile/${encodeURIComponent(String(health.profile_name))}`,
				String(health.profile_name)
			)
		: escape_html("Not created");
	const reviewedBy = render_user_link(health.reviewed_by);
	const reviewedOn = format_datetime(health.reviewed_on);
	const declaredBy = render_user_link(health.declared_by);
	const declaredOn = format_datetime(health.declared_on);

	return `
		<div style="margin-bottom: 10px;">
			${render_pill(health.status === "complete" ? "✓ Health Cleared" : reviewStatus, reviewTone)}
			<span style="margin-left: 6px;">${render_pill(health.declared_complete ? "✓ Declaration Complete" : "Declaration Pending", declarationTone)}</span>
		</div>
		<table class="table table-bordered" style="margin-bottom: 0;">
			<tbody>
				<tr>
					<th style="width: 24%;">Health Profile</th>
					<td>${profileLink}</td>
				</tr>
				<tr>
					<th>Review Status</th>
					<td>${escape_html(reviewStatus)}</td>
				</tr>
				<tr>
					<th>Reviewed By / On</th>
					<td>${reviewedBy} · ${escape_html(reviewedOn)}</td>
				</tr>
				<tr>
					<th>Declared By / On</th>
					<td>${declaredBy} · ${escape_html(declaredOn)}</td>
				</tr>
			</tbody>
		</table>
	`;
}

function render_policies(policies) {
	if (!policies) {
		return render_empty("No policy data.");
	}
	const rows = Array.isArray(policies.rows) ? policies.rows : [];
	if (!rows.length) {
		return render_empty("No required policies are in scope.");
	}

	const signedCount = rows.filter((row) => Boolean(row?.is_acknowledged)).length;
	const missing = Array.isArray(policies.missing) ? policies.missing : [];
	const tableRows = rows.map((row) => {
		const label = String(row?.label || row?.policy_key || row?.policy_title || row?.policy_name || "Policy");
		const version = String(row?.policy_version || "").trim();
		const signers = Array.isArray(row?.signers) ? row.signers : [];
		const statusPill = row?.is_acknowledged
			? render_pill("✓ Signed", "green")
			: render_pill("Pending", "amber");
		return `
			<tr>
				<td>${escape_html(label)}</td>
				<td>${statusPill}</td>
				<td>${render_signers(signers)}</td>
				<td>${escape_html(format_datetime(row?.acknowledged_at))}</td>
				<td>${version ? render_text_link(`/desk/policy-version/${encodeURIComponent(version)}`, version) : escape_html("—")}</td>
			</tr>
		`;
	}).join("");

	return `
		<div style="margin-bottom: 10px;">
			${render_pill(`${signedCount}/${rows.length} signed`, policies.ok ? "green" : "amber")}
			${missing.length ? `<span style="margin-left: 6px;">${render_pill(`Missing: ${missing.length}`, "red")}</span>` : ""}
		</div>
		<div class="table-responsive">
			<table class="table table-bordered table-sm" style="margin-bottom: 0;">
				<thead>
					<tr>
						<th>Policy</th>
						<th>Status</th>
						<th>Signed By</th>
						<th>Signed On</th>
						<th>Version</th>
					</tr>
				</thead>
				<tbody>
					${tableRows}
				</tbody>
			</table>
		</div>
	`;
}

function render_documents(documents) {
	if (!documents) {
		return render_empty("No document data.");
	}
	const requiredRows = Array.isArray(documents.required_rows) ? documents.required_rows : [];
	const uploadedRows = Array.isArray(documents.uploaded_rows) ? documents.uploaded_rows : [];
	const missing = Array.isArray(documents.missing) ? documents.missing : [];

	if (!requiredRows.length && !uploadedRows.length) {
		return render_empty("No document requirements are in scope.");
	}

	const requiredBody = requiredRows.map((row) => {
		const docName = String(row?.applicant_document || "").trim();
		const docLink = docName
			? render_text_link(`/desk/applicant-document/${encodeURIComponent(docName)}`, docName)
			: escape_html("—");
		const fileLink = row?.file_url ? render_text_link(String(row.file_url), "File", true) : escape_html("—");
		return `
			<tr>
				<td>${escape_html(String(row?.label || row?.document_type || "Document"))}</td>
				<td>${render_document_status_pill(row?.review_status)}</td>
				<td>${render_user_link(row?.uploaded_by)}</td>
				<td>${escape_html(format_datetime(row?.uploaded_at))}</td>
				<td>${render_user_link(row?.reviewed_by)}</td>
				<td>${escape_html(format_datetime(row?.reviewed_on))}</td>
				<td>${docLink} · ${fileLink}</td>
			</tr>
		`;
	}).join("");

	const uploadedBody = uploadedRows.map((row) => `
		<tr>
			<td>${escape_html(String(row?.label || row?.document_type || "Document"))}</td>
			<td>${render_document_status_pill(row?.review_status)}</td>
			<td>${render_user_link(row?.uploaded_by)}</td>
			<td>${escape_html(format_datetime(row?.uploaded_at))}</td>
			<td>${row?.file_url ? render_text_link(String(row.file_url), "File", true) : escape_html("—")}</td>
		</tr>
	`).join("");

	return `
		<div style="margin-bottom: 10px;">
			${render_pill(documents.ok ? "✓ All required documents approved" : "Action required", documents.ok ? "green" : "amber")}
			${missing.length ? `<span style="margin-left: 6px;">${render_pill(`Missing: ${missing.length}`, "red")}</span>` : ""}
		</div>
		${requiredRows.length ? `
			<div style="margin-bottom: 12px;">
				<div style="font-weight: 600; margin-bottom: 6px;">Required Documents</div>
				<div class="table-responsive">
					<table class="table table-bordered table-sm" style="margin-bottom: 0;">
						<thead>
							<tr>
								<th>Document</th>
								<th>Status</th>
								<th>Uploaded By</th>
								<th>Uploaded On</th>
								<th>Reviewed By</th>
								<th>Reviewed On</th>
								<th>Links</th>
							</tr>
						</thead>
						<tbody>
							${requiredBody}
						</tbody>
					</table>
				</div>
			</div>
		` : ""}
		${uploadedRows.length ? `
			<div>
				<div style="font-weight: 600; margin-bottom: 6px;">Latest Uploaded Documents</div>
				<div class="table-responsive">
					<table class="table table-bordered table-sm" style="margin-bottom: 0;">
						<thead>
							<tr>
								<th>Document</th>
								<th>Review Status</th>
								<th>Uploaded By</th>
								<th>Uploaded On</th>
								<th>File</th>
							</tr>
						</thead>
						<tbody>
							${uploadedBody}
						</tbody>
					</table>
				</div>
			</div>
		` : ""}
	`;
}

function render_ok_label(section) {
	if (!section) {
		return render_pill("Unknown", "slate");
	}
	return section.ok ? render_pill("✓ OK", "green") : render_pill("Needs Review", "amber");
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

function render_pill(text, tone = "slate") {
	const toneStyle = {
		green: "background:#e8f7ee;border:1px solid #9ad5b0;color:#1f7a3e;",
		amber: "background:#fff7e8;border:1px solid #f2cf88;color:#946200;",
		red: "background:#fdecec;border:1px solid #efb8b8;color:#a12424;",
		slate: "background:#f4f5f7;border:1px solid #d7dce2;color:#3f4b57;",
	};
	const style = toneStyle[tone] || toneStyle.slate;
	return `<span style="display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600;${style}">${escape_html(text)}</span>`;
}

function render_text_link(url, label, openInNewTab = false) {
	const safeUrl = String(url || "").trim();
	if (!safeUrl) {
		return escape_html("—");
	}
	const attrs = openInNewTab ? ' target="_blank" rel="noopener noreferrer"' : "";
	return `<a href="${escape_html(safeUrl)}"${attrs}>${escape_html(label || safeUrl)}</a>`;
}

function render_user_link(user) {
	const userName = String(user || "").trim();
	if (!userName) {
		return escape_html("—");
	}
	return render_text_link(`/desk/user/${encodeURIComponent(userName)}`, userName);
}

function render_signers(signers) {
	if (!Array.isArray(signers) || !signers.length) {
		return escape_html("—");
	}
	return signers.map((row) => render_user_link(row?.acknowledged_by)).join(", ");
}

function format_datetime(value) {
	const text = String(value || "").trim();
	if (!text) {
		return "—";
	}
	try {
		return frappe.datetime.str_to_user(text);
	} catch (error) {
		return text;
	}
}

function render_document_status_pill(status) {
	const normalized = String(status || "Pending").trim();
	if (normalized === "Approved") {
		return render_pill("Approved", "green");
	}
	if (normalized === "Rejected" || normalized === "Superseded") {
		return render_pill(normalized, "red");
	}
	if (normalized === "Missing") {
		return render_pill("Missing", "red");
	}
	return render_pill(normalized || "Pending", "amber");
}

function map_health_status(status) {
	if (status === "complete") {
		return "Cleared";
	}
	if (status === "needs_follow_up") {
		return "Needs Follow-Up";
	}
	if (status === "pending") {
		return "Pending Review";
	}
	if (status === "missing") {
		return "Missing";
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
