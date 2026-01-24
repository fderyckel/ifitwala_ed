// Copyright (c) 2024, fdR and contributors
// For license information, please see license.txt

frappe.ui.form.on("Student Applicant", {
	refresh(frm) {
		if (!frm.doc || frm.is_new()) {
			return;
		}
		frm.trigger("setup_governed_image_upload");
		render_review_sections(frm);
		add_decision_actions(frm);
	},

	setup_governed_image_upload(frm) {
		const fieldname = "applicant_image";

		frm.set_df_property(fieldname, "read_only", 1);
		frm.set_df_property(
			fieldname,
			"description",
			__("Use the Upload Applicant Image action to attach a governed file.")
		);

		frm.remove_custom_button(__("Upload Applicant Image"), __("Actions"));
		frm.add_custom_button(
			__("Upload Applicant Image"),
			() => {
				if (frm.is_new()) {
					frappe.msgprint(__("Please save the Student Applicant before uploading an image."));
					return;
				}

				new frappe.ui.FileUploader({
					method: "ifitwala_ed.utilities.governed_uploads.upload_applicant_image",
					args: { student_applicant: frm.doc.name },
					allow_multiple: false,
					on_success(file_doc) {
						if (!file_doc || !file_doc.file_url) {
							frappe.msgprint(__("Upload succeeded but no file URL was returned."));
							return;
						}
						frm.set_value(fieldname, file_doc.file_url);
						frm.refresh_field(fieldname);
					},
				});
			},
			__("Actions")
		);
	},
});

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
	return [
		render_line("Interview count", escape_html(String(count))),
	].join("");
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
	["Approve", "Reject", "Promote"].forEach((label) => frm.remove_custom_button(label));

	if (status === "Under Review") {
		frm.add_custom_button("Approve", () => {
			frappe.confirm("Approve this applicant?", () => {
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
				frm.call("promote_to_student")
					.then(() => frm.reload_doc())
					.catch((err) => {
						frappe.msgprint(err.message || "Unable to promote applicant.");
					});
			});
		});
	}
}
