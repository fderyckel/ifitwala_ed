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

const EMPLOYEE_USER_QUERY = "ifitwala_ed.api.users.get_users_with_role";

function get_employee_user_query() {
	return {
		query: EMPLOYEE_USER_QUERY,
		filters: { role: "Employee" },
	};
}

function get_employee_user_options(txt) {
	return frappe.call({
		type: "GET",
		method: "frappe.desk.search.search_link",
		args: {
			doctype: "User",
			txt: txt || "",
			query: EMPLOYEE_USER_QUERY,
			filters: { role: "Employee" },
		},
	}).then((res) => res?.message || []);
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
		add_enrollment_plan_action(frm);
		add_recommendation_actions(frm);
		add_create_interview_action(frm);
		add_schedule_interview_action(frm);
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
const TERMINAL_INTERVIEW_STATUSES = new Set(["Rejected", "Withdrawn", "Promoted"]);

function add_enrollment_plan_action(frm) {
	frm.remove_custom_button(__("Manage Enrollment Plan"), __("Actions"));
	frm.remove_custom_button(__("Manage Enrollment Plan"));

	if (!frm.doc || frm.is_new()) {
		return;
	}

	const status = String(frm.doc.application_status || "").trim();
	if (status === "Rejected" || status === "Withdrawn") {
		return;
	}

	frm.add_custom_button(__("Manage Enrollment Plan"), () => {
		frappe.call({
			method: "ifitwala_ed.admission.doctype.applicant_enrollment_plan.applicant_enrollment_plan.get_or_create_applicant_enrollment_plan",
			args: { student_applicant: frm.doc.name },
			freeze: true,
			freeze_message: __("Opening enrollment plan..."),
		}).then((res) => {
			const name = res?.message?.name;
			if (name) {
				frappe.set_route("Form", "Applicant Enrollment Plan", name);
			}
		}).catch((err) => {
			frappe.msgprint(err?.message || __("Unable to open the enrollment plan."));
		});
	}, __("Actions"));
}

function add_create_interview_action(frm) {
	frm.remove_custom_button(__("Create Interview"), __("Actions"));
	frm.remove_custom_button(__("Create Interview"));

	if (!frm.doc || frm.is_new()) {
		return;
	}

	const status = String(frm.doc.application_status || "").trim();
	if (TERMINAL_INTERVIEW_STATUSES.has(status)) {
		return;
	}

	frm.add_custom_button(__("Create Interview"), () => {
		frappe.new_doc(
			"Applicant Interview",
			{
				student_applicant: frm.doc.name,
				interview_date: frappe.datetime.get_today(),
			},
			(doc) => {
				const user = String(frappe.session.user || "").trim();
				if (!user) {
					return;
				}

				const rows = Array.isArray(doc.interviewers) ? doc.interviewers : [];
				const hasCurrentUser = rows.some(
					row => String(row?.interviewer || "").trim() === user
				);
				if (hasCurrentUser) {
					return;
				}

				const row = frappe.model.add_child(doc, "Applicant Interviewer", "interviewers");
				row.interviewer = user;
			}
		);
	}, __("Actions"));
}

function add_schedule_interview_action(frm) {
	frm.remove_custom_button(__("Schedule Interview"), __("Actions"));
	frm.remove_custom_button(__("Schedule Interview"));

	if (!frm.doc || frm.is_new()) {
		return;
	}

	const status = String(frm.doc.application_status || "").trim();
	if (TERMINAL_INTERVIEW_STATUSES.has(status)) {
		return;
	}

	frm.add_custom_button(__("Schedule Interview"), () => open_schedule_interview_dialog(frm), __("Actions"));
}

function open_schedule_interview_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Schedule Interview"),
		size: "large",
		fields: [
			{
				fieldname: "interview_date",
				fieldtype: "Date",
				label: __("Interview Date"),
				reqd: 1,
				default: frappe.datetime.get_today(),
			},
			{
				fieldname: "start_time",
				fieldtype: "Time",
				label: __("Start Time"),
				reqd: 1,
				default: "09:00:00",
			},
			{
				fieldname: "duration_minutes",
				fieldtype: "Int",
				label: __("Duration (minutes)"),
				reqd: 1,
				default: 30,
			},
			{
				fieldname: "column_break_interview_time",
				fieldtype: "Column Break",
			},
			{
				fieldname: "suggestion_window_start_time",
				fieldtype: "Time",
				label: __("Search Window Start"),
				default: "07:00:00",
			},
			{
				fieldname: "suggestion_window_end_time",
				fieldtype: "Time",
				label: __("Search Window End"),
				default: "17:00:00",
			},
			{
				fieldname: "section_break_people",
				fieldtype: "Section Break",
			},
			{
				fieldname: "primary_interviewer",
				fieldtype: "Link",
				options: "User",
				label: __("Primary Interviewer"),
				reqd: 1,
				default: frappe.session.user,
				get_query: () => get_employee_user_query(),
			},
			{
				fieldname: "additional_interviewers",
				fieldtype: "MultiSelectPills",
				label: __("Additional Interviewers"),
				description: __("Optional. Add more employee interviewers."),
				get_data: (txt) => get_employee_user_options(txt),
			},
			{
				fieldname: "column_break_people",
				fieldtype: "Column Break",
			},
			{
				fieldname: "interview_type",
				fieldtype: "Select",
				label: __("Interview Type"),
				options: "Family\nStudent\nJoint",
				default: "Student",
			},
			{
				fieldname: "mode",
				fieldtype: "Select",
				label: __("Mode"),
				options: "In Person\nOnline\nPhone",
				default: "In Person",
			},
			{
				fieldname: "confidentiality_level",
				fieldtype: "Select",
				label: __("Confidentiality Level"),
				options: "Admissions Team\nLeadership Only",
			},
			{
				fieldname: "notes",
				fieldtype: "Small Text",
				label: __("Notes"),
			},
			{
				fieldname: "suggestions_html",
				fieldtype: "HTML",
				label: __("Suggested Free Times"),
			},
		],
		primary_action_label: __("Schedule"),
		primary_action(values) {
			const interviewDate = String(values.interview_date || "").trim();
			const startTime = String(values.start_time || "").trim();
			const duration = Number(values.duration_minutes || 0);
			if (!interviewDate || !startTime) {
				frappe.msgprint(__("Interview date and start time are required."));
				return;
			}
			if (!duration || duration <= 0) {
				frappe.msgprint(__("Duration must be a positive number."));
				return;
			}

			const interviewerUsers = collect_interviewer_users(values);
			if (!interviewerUsers.length) {
				frappe.msgprint(__("Please select at least one interviewer."));
				return;
			}

			const interviewStart = `${interviewDate} ${startTime}`;

			d.disable_primary_action();
			frappe.call({
				method: "ifitwala_ed.admission.doctype.applicant_interview.applicant_interview.schedule_applicant_interview",
				args: {
					student_applicant: frm.doc.name,
					interview_start: interviewStart,
					duration_minutes: duration,
					interview_type: values.interview_type,
					mode: values.mode,
					confidentiality_level: values.confidentiality_level,
					notes: values.notes,
					primary_interviewer: values.primary_interviewer,
					interviewer_users: interviewerUsers,
					suggestion_window_start_time: values.suggestion_window_start_time,
					suggestion_window_end_time: values.suggestion_window_end_time,
				},
				freeze: true,
				freeze_message: __("Scheduling interview..."),
			})
				.then((res) => {
					const payload = res?.message || {};
					if (payload.ok) {
						frappe.show_alert({
							message: __("Interview scheduled."),
							indicator: "green",
						});
						d.hide();
						frm.reload_doc();
						return;
					}

					if (payload.code === "EMPLOYEE_CONFLICT") {
						render_suggestion_results(d, payload.suggestions || []);
						apply_first_suggestion(d, payload.suggestions || []);
						const conflictLabel = format_conflict_lines(payload.conflicts || []);
						frappe.msgprint({
							title: __("Interviewer Unavailable"),
							indicator: "orange",
							message: `
								<p>${__("One or more interviewers are already booked.")}</p>
								${conflictLabel}
								<p>${__("A suggested free time (if available) has been applied in the dialog.")}</p>
							`,
						});
						return;
					}

					frappe.msgprint({
						title: __("Unable to schedule interview"),
						indicator: "red",
						message: payload.message || __("Please review the form and try again."),
					});
				})
				.catch((err) => {
					frappe.msgprint({
						title: __("Unable to schedule interview"),
						indicator: "red",
						message: err?.message || __("Please try again."),
					});
				})
				.always(() => {
					d.enable_primary_action();
				});
		},
		secondary_action_label: __("Suggest Free Times"),
		secondary_action() {
			const values = d.get_values();
			const interviewDate = String(values?.interview_date || "").trim();
			const duration = Number(values?.duration_minutes || 0);
			const interviewerUsers = collect_interviewer_users(values || {});

			if (!interviewDate) {
				frappe.msgprint(__("Select an interview date first."));
				return;
			}
			if (!duration || duration <= 0) {
				frappe.msgprint(__("Duration must be a positive number."));
				return;
			}
			if (!interviewerUsers.length) {
				frappe.msgprint(__("Select at least one interviewer first."));
				return;
			}

			frappe.call({
				method: "ifitwala_ed.admission.doctype.applicant_interview.applicant_interview.suggest_interview_slots",
				args: {
					interview_date: interviewDate,
					primary_interviewer: values.primary_interviewer,
					interviewer_users: interviewerUsers,
					duration_minutes: duration,
					window_start_time: values.suggestion_window_start_time,
					window_end_time: values.suggestion_window_end_time,
				},
				freeze: true,
				freeze_message: __("Finding free times..."),
			})
				.then((res) => {
					const payload = res?.message || {};
					const suggestions = Array.isArray(payload.slots) ? payload.slots : [];
					render_suggestion_results(d, suggestions);
					apply_first_suggestion(d, suggestions);

					if (!suggestions.length) {
						frappe.msgprint({
							title: __("No free time found"),
							indicator: "orange",
							message: __("No common free slots were found in the selected search window."),
						});
					}
				})
				.catch((err) => {
					frappe.msgprint({
						title: __("Unable to fetch suggestions"),
						indicator: "red",
						message: err?.message || __("Please try again."),
					});
				});
		},
	});

	render_suggestion_results(d, []);
	d.show();
}

function collect_interviewer_users(values) {
	const out = [];
	const pushIf = (raw) => {
		const value = String(raw || "").trim();
		if (value) {
			out.push(value);
		}
	};

	pushIf(values.primary_interviewer);

	const additional = values.additional_interviewers;
	if (Array.isArray(additional)) {
		additional.forEach(pushIf);
	} else if (typeof additional === "string") {
		additional
			.split(",")
			.map(part => part.trim())
			.filter(Boolean)
			.forEach(pushIf);
	}

	return [...new Set(out)];
}

function render_suggestion_results(dialog, suggestions) {
	const field = dialog.get_field("suggestions_html");
	if (!field || !field.$wrapper) {
		return;
	}

	if (!Array.isArray(suggestions) || !suggestions.length) {
		field.$wrapper.html(`<div class="text-muted small">${__("No suggestions yet.")}</div>`);
		return;
	}

	const rows = suggestions
		.map((slot) => {
			const label = escape_html(String(slot?.label || ""));
			return `<li>${label}</li>`;
		})
		.join("");

	field.$wrapper.html(`
		<div class="small">
			<div style="margin-bottom: 4px;">${__("Suggested common free slots")}:</div>
			<ol style="padding-left: 18px; margin: 0;">${rows}</ol>
		</div>
	`);
}

function apply_first_suggestion(dialog, suggestions) {
	if (!Array.isArray(suggestions) || !suggestions.length) {
		return;
	}
	const first = suggestions[0];
	const start = String(first?.start || "");
	if (!start || start.length < 16) {
		return;
	}
	const datePart = start.slice(0, 10);
	const timePart = start.slice(11, 19);
	dialog.set_value("interview_date", datePart);
	dialog.set_value("start_time", timePart);
}

function format_conflict_lines(conflicts) {
	if (!Array.isArray(conflicts) || !conflicts.length) {
		return "";
	}
	const items = conflicts
		.slice(0, 10)
		.map((row) => {
			const employee = escape_html(String(row?.employee_name || row?.employee || "Employee"));
			const sourceDoctype = escape_html(String(row?.source_doctype || ""));
			const sourceName = escape_html(String(row?.source_name || ""));
			const bookingType = escape_html(String(row?.booking_type || "Booking"));
			const startLabel = escape_html(String(row?.start_label || ""));
			const endLabel = escape_html(String(row?.end_label || ""));
			return `<li><strong>${employee}</strong>: ${bookingType} (${sourceDoctype} ${sourceName}) ${startLabel} - ${endLabel}</li>`;
		})
		.join("");

	return `<ul style="margin-top: 8px; padding-left: 18px;">${items}</ul>`;
}

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
						description: __("Optional label to help staff distinguish this recommendation submission."),
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
			set_html(frm, "documents_summary", render_documents(data.documents, data.recommendations));
			bind_document_summary_actions(frm);
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

	const helperNote = `
		<div class="text-muted" style="margin-bottom: 8px;">
			Document review status and reviewer metadata are shown in Documents Summary below.
		</div>
	`;
	return `${helperNote}${sections || render_empty("No review assignment decisions yet.")}`;
}

function render_interviews(interviews) {
	if (!interviews) {
		return render_empty("No interview data.");
	}
	const count = Number(interviews.count || 0);
	const items = Array.isArray(interviews.items) ? interviews.items : [];
	if (!items.length) {
		return [
			render_line("Interview count", escape_html(String(count))),
			`<div class="text-muted" style="margin-top: 6px;">No interviews yet.</div>`,
		].join("");
	}

	const rows = items.map((row) => {
		const name = String(row?.name || "").trim();
		const scheduleLabel = escape_html(format_interview_schedule(row));
		const scheduleCell = name
			? `<a href="/desk/applicant-interview/${encodeURIComponent(name)}">${scheduleLabel}</a>`
			: scheduleLabel;
		const interviewerLabels = render_interviewer_labels(row);
		const impression = escape_html(String(row?.outcome_impression || "—"));
		return `
			<tr>
				<td>${scheduleCell}</td>
				<td>${interviewerLabels}</td>
				<td>${impression}</td>
			</tr>
		`;
	}).join("");

	return `
		<div style="margin-bottom: 6px;">${render_line("Interview count", escape_html(String(count)))}</div>
		<div class="table-responsive">
			<table class="table table-bordered table-sm" style="margin-bottom: 0;">
				<thead>
					<tr>
						<th>Date / Time</th>
						<th>Interviewer</th>
						<th>Outcome Impression</th>
					</tr>
				</thead>
				<tbody>
					${rows}
				</tbody>
			</table>
		</div>
	`;
}

function format_interview_schedule(row) {
	const interviewStart = String(row?.interview_start || "").trim();
	const interviewEnd = String(row?.interview_end || "").trim();
	const interviewDate = String(row?.interview_date || "").trim();
	if (interviewStart && interviewEnd) {
		return `${format_datetime(interviewStart)} - ${format_datetime(interviewEnd)}`;
	}
	if (interviewStart) {
		return format_datetime(interviewStart);
	}
	if (interviewDate) {
		return interviewDate;
	}
	return "—";
}

function render_interviewer_labels(row) {
	const labels = Array.isArray(row?.interviewer_labels)
		? row.interviewer_labels
			.map((value) => String(value || "").trim())
			.filter(Boolean)
		: [];
	if (labels.length) {
		return escape_html(labels.join(", "));
	}
	const interviewers = Array.isArray(row?.interviewers) ? row.interviewers : [];
	const fallback = interviewers
		.map((entry) => String(entry?.label || entry?.user || "").trim())
		.filter(Boolean);
	return escape_html(fallback.join(", ") || "—");
}

function render_health(health) {
	if (!health) {
		return render_empty("No health profile data.");
	}
	const requiredForApproval = health.required_for_approval !== false;
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
			${requiredForApproval ? "" : `<span style="margin-left: 6px;">${render_pill("Optional for approval", "slate")}</span>`}
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

function render_recommendation_review_section(recommendations) {
	const summary = recommendations || {};
	const rows = Array.isArray(summary?.review_rows) ? summary.review_rows : [];
	const pendingReviewCount = Number(summary?.pending_review_count || 0);

	const metrics = `
		<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin-bottom:12px;">
			<div style="border:1px solid #d7dce2;border-radius:12px;padding:10px 12px;background:#f8fbff;">
				<div class="text-muted" style="font-size:12px;">Required</div>
				<div style="font-weight:600;font-size:16px;">${escape_html(String(summary?.required_total || 0))}</div>
			</div>
			<div style="border:1px solid #d7dce2;border-radius:12px;padding:10px 12px;background:#f8fbff;">
				<div class="text-muted" style="font-size:12px;">Received</div>
				<div style="font-weight:600;font-size:16px;">${escape_html(String(summary?.received_total || 0))}</div>
			</div>
			<div style="border:1px solid #d7dce2;border-radius:12px;padding:10px 12px;background:#f8fbff;">
				<div class="text-muted" style="font-size:12px;">Requested</div>
				<div style="font-weight:600;font-size:16px;">${escape_html(String(summary?.requested_total || 0))}</div>
			</div>
			<div style="border:1px solid #d7dce2;border-radius:12px;padding:10px 12px;background:#f8fbff;">
				<div class="text-muted" style="font-size:12px;">Pending Review</div>
				<div style="font-weight:600;font-size:16px;">${escape_html(String(pendingReviewCount))}</div>
			</div>
		</div>
	`;

	if (!rows.length) {
		return `
			<div style="margin-bottom: 16px;">
				<div style="font-weight: 600; margin-bottom: 8px;">Recommendation Review</div>
				${metrics}
				<div class="text-muted">No submitted recommendations are available yet.</div>
			</div>
		`;
	}

	const body = rows.map((row) => {
		const recommendationRequest = String(row?.recommendation_request || "").trim();
		const recommendationSubmission = String(row?.recommendation_submission || "").trim();
		const applicantDocumentItem = String(row?.applicant_document_item || "").trim();
		const fileUrl = String(row?.file_url || "").trim();
		const actionButton = (
			recommendationRequest || recommendationSubmission || applicantDocumentItem
		)
			? `<button type="button" class="recommendation-review-action-btn" data-recommendation-request="${escape_html(recommendationRequest)}" data-recommendation-submission="${escape_html(recommendationSubmission)}" data-applicant-document-item="${escape_html(applicantDocumentItem)}" style="border:1px solid #d7dce2;background:#fff;color:#1f4b5c;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:600;">${escape_html("Review Recommendation")}</button>`
			: escape_html("—");
		const uploadedAt = format_human_moment(row?.submitted_on || row?.consumed_on);
		return `
			<tr>
				<td>
					<div style="font-weight: 600;">${escape_html(String(row?.recommender_name || row?.recommender_email || "Referee"))}</div>
					<div class="text-muted">${escape_html(String(row?.recommender_relationship || "—"))}</div>
				</td>
				<td>${escape_html(String(row?.template_name || row?.recommendation_template || "Recommendation"))}</td>
				<td>
					<div>${escape_html(format_human_moment(row?.sent_on))}</div>
					<div class="text-muted">${escape_html(format_human_moment(row?.opened_on))}</div>
				</td>
				<td>${escape_html(uploadedAt)}</td>
				<td>
					${render_document_status_pill(row?.review_status)}
					${row?.reviewed_by ? `<div class="text-muted" style="margin-top:4px;">${escape_html(String(row.reviewed_by))}</div>` : ""}
				</td>
				<td>
					${actionButton}
					${fileUrl ? `<div style="margin-top:6px;">${render_text_link(fileUrl, "Open attachment", true)}</div>` : ""}
				</td>
			</tr>
		`;
	}).join("");

	return `
		<div style="margin-bottom: 16px;">
			<div style="font-weight: 600; margin-bottom: 8px;">Recommendation Review</div>
			${metrics}
			<div class="table-responsive">
				<table class="table table-bordered table-sm" style="margin-bottom: 0;">
					<thead>
						<tr>
							<th>Referee</th>
							<th>Template</th>
							<th>Shared / Opened</th>
							<th>Submitted</th>
							<th>Review Status</th>
							<th>Actions</th>
						</tr>
					</thead>
					<tbody>
						${body}
					</tbody>
				</table>
			</div>
		</div>
	`;
}

function render_documents(documents, recommendations) {
	if (!documents) {
		return render_empty("No document data.");
	}
	const requiredRows = Array.isArray(documents.required_rows) ? documents.required_rows : [];
	const uploadedRows = Array.isArray(documents.uploaded_rows) ? documents.uploaded_rows : [];
	const missing = Array.isArray(documents.missing) ? documents.missing : [];
	const pendingUploadedReviews = uploadedRows.filter((row) => {
		const status = String(row?.review_status || "Pending").trim() || "Pending";
		return status === "Pending";
	}).length;

	if (!requiredRows.length && !uploadedRows.length) {
		return render_empty("No document requirements are in scope.");
	}
	const canManageOverrides = can_manage_document_overrides();
	const canReviewSubmissions = can_review_document_submissions();

	const requiredBody = requiredRows.map((row) => {
		const docName = String(row?.applicant_document || "").trim();
		const fileLink = row?.file_url ? render_text_link(String(row.file_url), "Open latest file", true) : escape_html("—");
		const requirementOverride = String(row?.requirement_override || "").trim();
		const overrideReason = String(row?.override_reason || "").trim();
		const overrideMeta = requirementOverride
			? `<div class="text-muted" style="margin-top: 4px;">${escape_html(overrideReason || "Override recorded.")}</div>`
			: "";
		const actionButtons = canManageOverrides
			? requirementOverride
				? `<button type="button" class="document-requirement-action-btn" data-action="clear_override" data-applicant-document="${escape_html(docName)}" data-document-type="${escape_html(String(row?.document_type || ""))}" style="margin-right: 6px; border:1px solid #d7dce2; background:#fff; color:#3f4b57; border-radius:999px; padding:4px 10px; font-size:12px; font-weight:600;">${escape_html("Clear Override")}</button>`
				: [
					`<button type="button" class="document-requirement-action-btn" data-action="set_override" data-override="Waived" data-applicant-document="${escape_html(docName)}" data-document-type="${escape_html(String(row?.document_type || ""))}" data-label="${escape_html(String(row?.label || row?.document_type || "Requirement"))}" style="margin-right: 6px; border:1px solid #d7dce2; background:#fff; color:#3f4b57; border-radius:999px; padding:4px 10px; font-size:12px; font-weight:600;">${escape_html("Waive")}</button>`,
					`<button type="button" class="document-requirement-action-btn" data-action="set_override" data-override="Exception Approved" data-applicant-document="${escape_html(docName)}" data-document-type="${escape_html(String(row?.document_type || ""))}" data-label="${escape_html(String(row?.label || row?.document_type || "Requirement"))}" style="border:1px solid #d7dce2; background:#fff; color:#3f4b57; border-radius:999px; padding:4px 10px; font-size:12px; font-weight:600;">${escape_html("Exception")}</button>`,
				].join("")
			: escape_html("—");
		return `
			<tr>
				<td>${escape_html(String(row?.label || row?.document_type || "Document"))}</td>
				<td>${render_document_status_pill(row?.review_status)}${overrideMeta}</td>
				<td>${render_approved_required_pill(row)}</td>
				<td>${render_user_link(row?.uploaded_by)}<div class="text-muted">${escape_html(format_datetime(row?.uploaded_at))}</div></td>
				<td>${render_user_link(row?.reviewed_by)}<div class="text-muted">${escape_html(format_datetime(row?.reviewed_on))}</div></td>
				<td>${fileLink}</td>
				<td>${actionButtons}</td>
			</tr>
		`;
	}).join("");

	const uploadedBody = uploadedRows.map((row) => `
		<tr>
			<td>${escape_html(String(row?.document_label || row?.document_type || "Document"))}</td>
			<td>${escape_html(String(row?.item_label || row?.item_key || row?.applicant_document_item || "Submission"))}</td>
			<td>${render_document_status_pill(row?.review_status)}</td>
			<td>${render_user_link(row?.uploaded_by)}<div class="text-muted">${escape_html(format_datetime(row?.uploaded_at))}</div></td>
			<td>${render_user_link(row?.reviewed_by)}<div class="text-muted">${escape_html(format_datetime(row?.reviewed_on))}</div></td>
			<td>${row?.file_url ? render_text_link(String(row.file_url), "Open file", true) : escape_html("—")}</td>
			<td>${canReviewSubmissions ? render_submission_action_buttons(row) : escape_html("—")}</td>
		</tr>
	`).join("");

	return `
		<div style="margin-bottom: 10px;">
			${render_pill(documents.ok ? "✓ All required document requirements complete" : "Action required", documents.ok ? "green" : "amber")}
			${missing.length ? `<span style="margin-left: 6px;">${render_pill(`Missing: ${missing.length}`, "red")}</span>` : ""}
			${pendingUploadedReviews ? `<span style="margin-left: 6px;">${render_pill(`Pending item reviews: ${pendingUploadedReviews}`, "amber")}</span>` : ""}
		</div>
		${render_recommendation_review_section(recommendations)}
		${requiredRows.length ? `
			<div style="margin-bottom: 12px;">
				<div style="font-weight: 600; margin-bottom: 6px;">Document Requirements</div>
				<div class="table-responsive">
					<table class="table table-bordered table-sm" style="margin-bottom: 0;">
						<thead>
							<tr>
								<th>Document</th>
								<th>Status</th>
								<th>Approved / Required</th>
								<th>Latest Upload</th>
								<th>Latest Review</th>
								<th>File</th>
								<th>Actions</th>
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
				<div style="font-weight: 600; margin-bottom: 6px;">Submitted Files</div>
				<div class="table-responsive">
					<table class="table table-bordered table-sm" style="margin-bottom: 0;">
						<thead>
							<tr>
								<th>Requirement</th>
								<th>Submission</th>
								<th>Review Status</th>
								<th>Uploaded</th>
								<th>Reviewed</th>
								<th>File</th>
								<th>Actions</th>
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

function can_manage_document_overrides() {
	return ["Admission Manager", "Academic Admin", "System Manager"].some((role) => frappe.user.has_role(role));
}

function can_review_document_submissions() {
	return ["Admission Officer", "Admission Manager", "Academic Admin", "System Manager"].some((role) => frappe.user.has_role(role));
}

function new_admissions_review_request_id(prefix = "admissions_review") {
	return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2, 12)}`;
}

function render_submission_action_buttons(row) {
	const itemName = String(row?.applicant_document_item || "").trim();
	if (!itemName) {
		return escape_html("—");
	}
	const attrs = `data-applicant-document-item="${escape_html(itemName)}" data-label="${escape_html(String(row?.label || row?.item_label || row?.item_key || "Submission"))}"`;
	return [
		`<button type="button" class="document-submission-action-btn" data-action="approve_submission" ${attrs} style="margin-right: 6px; border:1px solid #d7dce2; background:#fff; color:#3f4b57; border-radius:999px; padding:4px 10px; font-size:12px; font-weight:600;">${escape_html("Approve")}</button>`,
		`<button type="button" class="document-submission-action-btn" data-action="needs_follow_up_submission" ${attrs} style="margin-right: 6px; border:1px solid #d7dce2; background:#fff; color:#3f4b57; border-radius:999px; padding:4px 10px; font-size:12px; font-weight:600;">${escape_html("Request Changes")}</button>`,
		`<button type="button" class="document-submission-action-btn" data-action="reject_submission" ${attrs} style="border:1px solid #d7dce2; background:#fff; color:#3f4b57; border-radius:999px; padding:4px 10px; font-size:12px; font-weight:600;">${escape_html("Reject")}</button>`,
	].join("");
}

function bind_document_summary_actions(frm) {
	const wrapper = frm.fields_dict.documents_summary?.$wrapper;
	if (!wrapper) {
		return;
	}

	wrapper.off("click", ".document-requirement-action-btn");
	wrapper.on("click", ".document-requirement-action-btn", (event) => {
		const target = event.currentTarget;
		if (!(target instanceof HTMLElement)) {
			return;
		}
		const action = String(target.getAttribute("data-action") || "").trim();
		const applicantDocument = String(target.getAttribute("data-applicant-document") || "").trim();
		const documentType = String(target.getAttribute("data-document-type") || "").trim();
		const overrideValue = String(target.getAttribute("data-override") || "").trim();
		const label = String(target.getAttribute("data-label") || documentType || applicantDocument || "Requirement").trim();

		if (action === "clear_override") {
			frappe.confirm(__("Clear the requirement override for {0}?").replace("{0}", label), () => {
				apply_document_requirement_override(frm, {
					applicant_document: applicantDocument || null,
					document_type: documentType || null,
					requirement_override: "",
					override_reason: "",
				});
			});
			return;
		}

		if (action !== "set_override" || !overrideValue) {
			return;
		}

		frappe.prompt(
			[
				{
					label: __("Reason"),
					fieldname: "override_reason",
					fieldtype: "Small Text",
					reqd: 1,
				},
			],
			(values) => {
				apply_document_requirement_override(frm, {
					applicant_document: applicantDocument || null,
					document_type: documentType || null,
					requirement_override: overrideValue,
					override_reason: String(values.override_reason || "").trim(),
				});
			},
			__(overrideValue),
			__("Apply")
		);
	});

	wrapper.off("click", ".document-submission-action-btn");
	wrapper.on("click", ".document-submission-action-btn", (event) => {
		const target = event.currentTarget;
		if (!(target instanceof HTMLElement)) {
			return;
		}
		const action = String(target.getAttribute("data-action") || "").trim();
		const applicantDocumentItem = String(target.getAttribute("data-applicant-document-item") || "").trim();
		const label = String(target.getAttribute("data-label") || applicantDocumentItem || "Submission").trim();
		if (!action || !applicantDocumentItem) {
			return;
		}

		if (action === "approve_submission") {
			frappe.confirm(__("Approve the submitted file for {0}?").replace("{0}", label), () => {
				review_document_submission(frm, {
					applicant_document_item: applicantDocumentItem,
					decision: "Approved",
					notes: "",
				});
			});
			return;
		}

		const decision = action === "needs_follow_up_submission" ? "Needs Follow-Up" : action === "reject_submission" ? "Rejected" : "";
		if (!decision) {
			return;
		}

		frappe.prompt(
			[
				{
					label: __("Review Note"),
					fieldname: "notes",
					fieldtype: "Small Text",
					reqd: 1,
				},
			],
			(values) => {
				review_document_submission(frm, {
					applicant_document_item: applicantDocumentItem,
					decision,
					notes: String(values.notes || "").trim(),
				});
			},
			decision === "Needs Follow-Up" ? __("Request Changes") : __("Reject Submission"),
			__("Save")
		);
	});

	wrapper.off("click", ".recommendation-review-action-btn");
	wrapper.on("click", ".recommendation-review-action-btn", (event) => {
		const target = event.currentTarget;
		if (!(target instanceof HTMLElement)) {
			return;
		}
		open_recommendation_review_dialog(frm, {
			recommendation_request: String(target.getAttribute("data-recommendation-request") || "").trim(),
			recommendation_submission: String(target.getAttribute("data-recommendation-submission") || "").trim(),
			applicant_document_item: String(target.getAttribute("data-applicant-document-item") || "").trim(),
		});
	});
}

function render_recommendation_review_dialog(payload) {
	const recommendation = payload?.recommendation || {};
	const answers = Array.isArray(recommendation.answers) ? recommendation.answers : [];
	const canReviewSubmissions = can_review_document_submissions();
	const canReview = Boolean(
		recommendation.can_review &&
		recommendation.applicant_document_item &&
		canReviewSubmissions
	);
	const reviewStatus = String(recommendation.review_status || "Pending").trim() || "Pending";

	const timelineRows = [
		{ label: "Shared", value: recommendation.sent_on },
		{ label: "Opened", value: recommendation.opened_on },
		{ label: "Submitted", value: recommendation.submitted_on },
		{ label: "Reviewed", value: recommendation.reviewed_on },
	];

	const timelineBody = timelineRows.map((row) => `
		<div style="border:1px solid #d7dce2;border-radius:12px;padding:10px 12px;background:#fff;">
			<div class="text-muted" style="font-size:12px;">${escape_html(row.label)}</div>
			<div style="font-weight:600;">${escape_html(format_human_moment(row.value))}</div>
		</div>
	`).join("");

	const answerBody = answers.length
		? answers.map((answer) => `
			<div style="border:1px solid #d7dce2;border-radius:12px;padding:12px;background:#fff;margin-bottom:8px;">
				<div class="text-muted" style="font-size:12px;margin-bottom:4px;">${escape_html(String(answer?.label || answer?.field_key || "Answer"))}</div>
				<div style="white-space:pre-wrap;">${escape_html(String(answer?.display_value || (answer?.has_value ? answer?.value || "" : "No response")))}</div>
			</div>
		`).join("")
		: `<div class="text-muted">No structured answers were captured for this recommendation.</div>`;

	const reviewActions = canReview
		? `
			<div style="margin-top:16px;border-top:1px solid #e5e7eb;padding-top:12px;">
				<label style="display:block;margin-bottom:8px;">
					<div class="text-muted" style="font-size:12px;margin-bottom:4px;">Review Note</div>
					<textarea class="recommendation-review-note" rows="3" placeholder="Required for Request Changes or Reject" style="width:100%;border:1px solid #d7dce2;border-radius:12px;padding:10px 12px;resize:vertical;"></textarea>
				</label>
				<div style="display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px;">
					<button type="button" class="recommendation-review-decision-btn" data-decision="Approved" style="border:1px solid #d7dce2;background:#fff;color:#1f4b5c;border-radius:999px;padding:6px 12px;font-size:12px;font-weight:600;">${escape_html("Approve")}</button>
					<button type="button" class="recommendation-review-decision-btn" data-decision="Needs Follow-Up" style="border:1px solid #d7dce2;background:#fff;color:#1f4b5c;border-radius:999px;padding:6px 12px;font-size:12px;font-weight:600;">${escape_html("Request Changes")}</button>
					<button type="button" class="recommendation-review-decision-btn" data-decision="Rejected" style="border:1px solid #d7dce2;background:#fff;color:#1f4b5c;border-radius:999px;padding:6px 12px;font-size:12px;font-weight:600;">${escape_html("Reject")}</button>
				</div>
			</div>
		`
		: `<div class="text-muted" style="margin-top: 12px;">${
			canReviewSubmissions
				? escape_html(__("This recommendation has already been reviewed."))
				: escape_html(__("You can view this recommendation here, but only admissions reviewers can record a decision."))
		}</div>`;

	return `
		<div style="display:grid;gap:16px;">
			<div style="display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px;align-items:flex-start;">
				<div>
					<div class="text-muted" style="font-size:12px;">Recommendation Review</div>
					<div style="font-size:20px;font-weight:700;color:#17313b;">${escape_html(String(recommendation.recommender_name || recommendation.recommender_email || "Referee"))}</div>
					<div class="text-muted" style="margin-top:4px;">${escape_html(String(recommendation.template_name || recommendation.recommendation_template || "Recommendation"))}${recommendation.recommender_relationship ? ` · ${escape_html(String(recommendation.recommender_relationship))}` : ""}</div>
				</div>
				<div>${render_document_status_pill(reviewStatus)}</div>
			</div>
			<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;">
				${timelineBody}
			</div>
			<div style="border:1px solid #d7dce2;border-radius:12px;padding:12px;background:#f8fbff;">
				<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
					${recommendation.attestation_confirmed ? `<span style="display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600;background:#e8f7ee;border:1px solid #9ad5b0;color:#1f7a3e;">${escape_html("Attestation confirmed")}</span>` : ""}
					${recommendation.item_label ? `<span style="display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600;background:#f4f5f7;border:1px solid #d7dce2;color:#3f4b57;">${escape_html(String(recommendation.item_label))}</span>` : ""}
					${recommendation.file_url ? render_text_link(String(recommendation.file_url), recommendation.file_name || "Open attached file", true) : ""}
				</div>
				${recommendation.recommender_email ? `<div class="text-muted" style="margin-top:8px;">${escape_html(String(recommendation.recommender_email))}</div>` : ""}
			</div>
			<div>
				<div style="font-weight:600;margin-bottom:8px;">Submission Answers</div>
				${answerBody}
			</div>
			${reviewActions}
		</div>
	`;
}

function normalize_recommendation_review_anchor(anchor) {
	const recommendationRequest = String(anchor?.recommendation_request || "").trim();
	if (recommendationRequest) {
		return { recommendation_request: recommendationRequest };
	}
	const recommendationSubmission = String(anchor?.recommendation_submission || "").trim();
	if (recommendationSubmission) {
		return { recommendation_submission: recommendationSubmission };
	}
	const applicantDocumentItem = String(anchor?.applicant_document_item || "").trim();
	if (applicantDocumentItem) {
		return { applicant_document_item: applicantDocumentItem };
	}
	return null;
}

function open_recommendation_review_dialog(frm, anchor) {
	const dialog = new frappe.ui.Dialog({
		title: __("Recommendation Review"),
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

	let currentPayload = null;
	let currentAnchor = normalize_recommendation_review_anchor(anchor);

	const renderLoading = () => {
		dialog.fields_dict.body.$wrapper.html(`<div class="text-muted">${escape_html("Loading recommendation review...")}</div>`);
	};

	const loadPayload = () => {
		if (!currentAnchor) {
			dialog.fields_dict.body.$wrapper.html(
				`<div class="text-danger">${escape_html(__("Recommendation reference is missing."))}</div>`
			);
			return Promise.resolve();
		}
		renderLoading();
		return frappe.call({
			method: "ifitwala_ed.api.recommendation_intake.get_recommendation_review_payload",
			args: {
				student_applicant: frm.doc.name,
				recommendation_request: currentAnchor.recommendation_request || null,
				recommendation_submission: currentAnchor.recommendation_submission || null,
				applicant_document_item: currentAnchor.applicant_document_item || null,
			},
		}).then((res) => {
			currentPayload = res?.message || {};
			dialog.fields_dict.body.$wrapper.html(render_recommendation_review_dialog(currentPayload));
		}).catch((error) => {
			dialog.fields_dict.body.$wrapper.html(
				`<div class="text-danger">${escape_html(get_error_message(error, __("Unable to load recommendation review.")))}</div>`
			);
		});
	};

	dialog.$wrapper.off("click", ".recommendation-review-decision-btn");
	dialog.$wrapper.on("click", ".recommendation-review-decision-btn", (event) => {
		const target = event.currentTarget;
		if (!(target instanceof HTMLElement)) {
			return;
		}
		const decision = String(target.getAttribute("data-decision") || "").trim();
		const applicantDocumentItem = String(currentPayload?.recommendation?.applicant_document_item || "").trim();
		const notes = String(dialog.$wrapper.find(".recommendation-review-note").val() || "").trim();
		if (!decision || !applicantDocumentItem) {
			frappe.msgprint(__("Recommendation review target is missing."));
			return;
		}
		if ((decision === "Needs Follow-Up" || decision === "Rejected") && !notes) {
			frappe.msgprint(__("A review note is required for this decision."));
			return;
		}
		review_document_submission(
			frm,
			{
				applicant_document_item: applicantDocumentItem,
				decision,
				notes,
			},
			{
				show_alert: false,
				success_message: __("Recommendation review updated."),
				on_success: () => loadPayload(),
			}
		);
	});

	dialog.show();
	loadPayload();
}

function apply_document_requirement_override(frm, payload) {
	frappe.call({
		method: "ifitwala_ed.api.admissions_review.set_document_requirement_override",
		args: {
			student_applicant: frm.doc.name,
			...payload,
			client_request_id: new_admissions_review_request_id("document_requirement_override"),
		},
		freeze: true,
		freeze_message: __("Updating requirement override..."),
	})
		.then(() => {
			frappe.show_alert({ message: __("Requirement override updated."), indicator: "green" });
			render_review_sections(frm);
		})
		.catch((error) => {
			frappe.msgprint(get_error_message(error, __("Unable to update requirement override.")));
		});
}

function review_document_submission(frm, payload, options = {}) {
	frappe.call({
		method: "ifitwala_ed.api.admissions_review.review_applicant_document_submission",
		args: {
			student_applicant: frm.doc.name,
			...payload,
			client_request_id: new_admissions_review_request_id("document_submission_review"),
		},
		freeze: true,
		freeze_message: __("Saving evidence review..."),
	})
		.then(() => {
			if (options.show_alert !== false) {
				frappe.show_alert({ message: options.success_message || __("Submitted file review updated."), indicator: "green" });
			}
			render_review_sections(frm);
			if (typeof options.on_success === "function") {
				options.on_success();
			}
		})
		.catch((error) => {
			frappe.msgprint(get_error_message(error, __("Unable to update submitted file review.")));
		});
}

function render_ok_label(section) {
	if (!section) {
		return render_pill("Unknown", "slate");
	}
	if (section.required_for_approval === false) {
		return section.ok ? render_pill("Optional - Complete", "slate") : render_pill("Optional", "slate");
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

function parse_datetime_value(value) {
	const text = String(value || "").trim();
	if (!text) {
		return null;
	}
	const normalized = text.replace(" ", "T").replace(/\.(\d{3})\d+/, ".$1");
	const parsed = new Date(normalized);
	if (!Number.isNaN(parsed.getTime())) {
		return parsed;
	}
	const fallback = new Date(text);
	return Number.isNaN(fallback.getTime()) ? null : fallback;
}

function format_relative_time(value) {
	const parsed = parse_datetime_value(value);
	if (!parsed || typeof Intl === "undefined" || typeof Intl.RelativeTimeFormat !== "function") {
		return "";
	}
	const diffSeconds = Math.round((parsed.getTime() - Date.now()) / 1000);
	const absoluteSeconds = Math.abs(diffSeconds);
	const formatter = new Intl.RelativeTimeFormat((frappe.boot && frappe.boot.lang) || undefined, {
		numeric: "auto",
	});
	if (absoluteSeconds < 60) {
		return formatter.format(diffSeconds, "second");
	}
	if (absoluteSeconds < 3600) {
		return formatter.format(Math.round(diffSeconds / 60), "minute");
	}
	if (absoluteSeconds < 86400) {
		return formatter.format(Math.round(diffSeconds / 3600), "hour");
	}
	if (absoluteSeconds < 604800) {
		return formatter.format(Math.round(diffSeconds / 86400), "day");
	}
	if (absoluteSeconds < 2629800) {
		return formatter.format(Math.round(diffSeconds / 604800), "week");
	}
	return formatter.format(Math.round(diffSeconds / 2629800), "month");
}

function format_human_moment(value) {
	const absolute = format_datetime(value);
	if (absolute === "—") {
		return absolute;
	}
	const relative = format_relative_time(value);
	return relative ? `${absolute} (${relative})` : absolute;
}

function render_document_status_pill(status) {
	const normalized = String(status || "Pending").trim();
	if (normalized === "Approved" || normalized === "Waived" || normalized === "Exception Approved") {
		return render_pill(normalized, "green");
	}
	if (normalized === "Rejected") {
		return render_pill("Rejected", "red");
	}
	if (normalized === "Superseded") {
		return render_pill("Superseded", "slate");
	}
	if (normalized === "Needs Follow-Up") {
		return render_pill("Needs Follow-Up", "amber");
	}
	if (normalized === "Missing") {
		return render_pill("Missing", "red");
	}
	return render_pill(normalized || "Pending", "amber");
}

function render_approved_required_pill(row) {
	const requirementOverride = String(row?.requirement_override || "").trim();
	if (requirementOverride) {
		return render_pill(requirementOverride, "green");
	}
	const requiredCount = Number(row?.required_count || 0);
	if (!requiredCount) {
		return escape_html("—");
	}
	const approvedCount = Number(row?.approved_count || 0);
	const tone = approvedCount >= requiredCount ? "green" : "amber";
	return render_pill(`${approvedCount}/${requiredCount}`, tone);
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
