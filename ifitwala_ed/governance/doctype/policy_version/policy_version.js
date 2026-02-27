// ifitwala_ed/governance/doctype/policy_version/policy_version.js
// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Policy Version", {
	setup(frm) {
		frm.set_query("approved_by", () => ({
			query: "ifitwala_ed.governance.doctype.policy_version.policy_version.approved_by_user_query",
			filters: {
				institutional_policy: frm.doc.institutional_policy || "",
			},
		}));
		frm.set_query("amended_from", () => ({
			filters: {
				institutional_policy: frm.doc.institutional_policy || "",
				name: ["!=", frm.doc.name || ""],
			},
		}));
	},
	refresh(frm) {
		if (frm.is_new() || !frm.doc.name || !frm.doc.institutional_policy) return;

		frm.add_custom_button(__("Create Amendment"), () => {
			const currentLabel = String(frm.doc.version_label || "").trim();
			const suggestion = suggestNextVersionLabel(currentLabel || "v1");
			const newDoc = frappe.model.get_new_doc("Policy Version");

			newDoc.institutional_policy = frm.doc.institutional_policy;
			newDoc.version_label = suggestion;
			newDoc.amended_from = frm.doc.name;
			newDoc.change_summary = "";
			newDoc.policy_text = frm.doc.policy_text || "";
			newDoc.is_active = 0;
			newDoc.approved_by = "";
			newDoc.approved_on = "";
			newDoc.effective_from = "";
			newDoc.effective_to = "";

			frappe.set_route("Form", "Policy Version", newDoc.name);
			frappe.show_alert({
				message: __("Draft amendment created. Update summary/text, then save and activate."),
				indicator: "blue",
			});
		});

		frm.add_custom_button(__("Share Amendment"), () => {
			openShareAmendmentDialog(frm);
		});
	},
});

function suggestNextVersionLabel(label) {
	const value = String(label || "").trim();
	if (!value) return "v1";

	const match = value.match(/^(.*?)(\d+)$/);
	if (match) {
		const prefix = match[1] || "";
		const number = Number.parseInt(match[2], 10);
		if (Number.isFinite(number)) {
			return `${prefix}${number + 1}`;
		}
	}

	return `${value}-amend-1`;
}

function todayDate() {
	return frappe.datetime.get_today();
}

function addDays(dateStr, days) {
	return frappe.datetime.add_days(dateStr, days);
}

function parseChangeStats(raw) {
	if (!raw) return { added: 0, removed: 0, modified: 0 };
	if (typeof raw === "object") {
		return {
			added: Number(raw.added || 0),
			removed: Number(raw.removed || 0),
			modified: Number(raw.modified || 0),
		};
	}
	try {
		const parsed = JSON.parse(String(raw));
		return {
			added: Number(parsed.added || 0),
			removed: Number(parsed.removed || 0),
			modified: Number(parsed.modified || 0),
		};
	} catch (error) {
		return { added: 0, removed: 0, modified: 0 };
	}
}

function buildPolicyMessageHtml(frm, policyMeta) {
	const policyLabel =
		String(policyMeta.policy_title || "").trim() ||
		String(policyMeta.policy_key || "").trim() ||
		String(frm.doc.institutional_policy || "").trim() ||
		String(frm.doc.name || "").trim();
	const versionLabel = String(frm.doc.version_label || "").trim();
	const summary = String(frm.doc.change_summary || "").trim();
	const diffHtml = String(frm.doc.diff_html || "").trim();
	const stats = parseChangeStats(frm.doc.change_stats);
	const route = `/app/policy-version/${encodeURIComponent(String(frm.doc.name || "").trim())}`;

	const parts = [
		`<h3>${frappe.utils.escape_html(policyLabel)}${versionLabel ? ` - Version ${frappe.utils.escape_html(versionLabel)}` : ""}</h3>`,
	];
	if (summary) {
		parts.push(`<p><strong>What changed</strong><br>${frappe.utils.escape_html(summary)}</p>`);
	}
	parts.push(
		`<p>Added: ${stats.added}<br>Removed: ${stats.removed}<br>Modified: ${stats.modified}</p>`
	);
	if (diffHtml) {
		parts.push("<hr><h4>Detailed changes</h4>");
		parts.push(diffHtml);
	}
	parts.push(`<hr><p><a href="${route}">Open policy version in Desk</a></p>`);

	return parts.join("");
}

function defaultRecipients(policyMeta) {
	const appliesTo = String(policyMeta.applies_to || "").trim();
	if (appliesTo === "Student") {
		return { to_staff: 0, to_students: 1, to_guardians: 0, to_community: 0 };
	}
	if (appliesTo === "Guardian") {
		return { to_staff: 0, to_students: 0, to_guardians: 1, to_community: 0 };
	}
	if (appliesTo === "Applicant") {
		return { to_staff: 0, to_students: 1, to_guardians: 1, to_community: 0 };
	}
	return { to_staff: 1, to_students: 0, to_guardians: 0, to_community: 0 };
}

function defaultTargetScope(policyMeta) {
	return policyMeta.policy_school ? "School" : "Organization (All Schools)";
}

async function getInstitutionalPolicyMeta(policyName) {
	const response = await frappe.call({
		method: "frappe.client.get_value",
		args: {
			doctype: "Institutional Policy",
			filters: { name: policyName },
			fieldname: ["name", "policy_title", "policy_key", "organization", "school", "applies_to"],
		},
	});
	return response?.message || {};
}

async function openShareAmendmentDialog(frm) {
	if (!frm.doc.name) return;
	if (!frm.doc.policy_text || !String(frm.doc.policy_text).trim()) {
		frappe.msgprint(__("Policy Text is required before sharing."));
		return;
	}

	let policyMeta = {};
	try {
		policyMeta = await getInstitutionalPolicyMeta(frm.doc.institutional_policy);
	} catch (error) {
		frappe.msgprint(__("Unable to load policy context for sharing."));
		return;
	}

	const policyLabel =
		String(policyMeta.policy_title || "").trim() ||
		String(policyMeta.policy_key || "").trim() ||
		String(frm.doc.institutional_policy || "").trim() ||
		String(frm.doc.name || "").trim();
	const versionLabel = String(frm.doc.version_label || "").trim();
	const defaultTitle = versionLabel
		? `${policyLabel} - Version ${versionLabel} update`
		: `${policyLabel} update`;
	const recipientDefaults = defaultRecipients(policyMeta);
	const isStaffPolicy = String(policyMeta.applies_to || "").trim() === "Staff";

	let d = null;
	const submitAction = async values => {
		if (values.brief_start_date && values.brief_end_date && values.brief_end_date < values.brief_start_date) {
			frappe.msgprint(__("Brief End Date cannot be before Brief Start Date."));
			return;
		}
		if (!values.message_html || !String(values.message_html).trim()) {
			frappe.msgprint(__("Communication Content is required."));
			return;
		}
		if (values.target_scope === "School" && !values.target_school) {
			frappe.msgprint(__("School is required for School scope."));
			return;
		}
		if (values.target_scope === "Team" && !values.target_team) {
			frappe.msgprint(__("Team is required for Team scope."));
			return;
		}
		if (!values.to_staff && !values.to_students && !values.to_guardians && !values.to_community) {
			frappe.msgprint(__("Select at least one recipient type."));
			return;
		}
		if (values.target_scope === "Team" && (values.to_students || values.to_guardians || values.to_community)) {
			frappe.msgprint(__("Team scope supports Staff recipients only."));
			return;
		}
		if (values.create_signature_campaign && !isStaffPolicy) {
			frappe.msgprint(__("Signature campaign can only be created for Staff policies."));
			return;
		}

		d.set_primary_action(__("Creating..."), () => {});
		d.disable_primary_action();

		try {
			const response = await frappe.call({
				method: "ifitwala_ed.api.policy_communication.create_policy_amendment_communication",
				args: {
					policy_version: frm.doc.name,
					title: values.title,
					message_html: values.message_html,
					target_scope: values.target_scope,
					target_school: values.target_school || null,
					target_team: values.target_team || null,
					brief_start_date: values.brief_start_date,
					brief_end_date: values.brief_end_date,
					publish_from: values.publish_from || null,
					publish_to: values.publish_to || null,
					create_signature_campaign: values.create_signature_campaign ? 1 : 0,
					campaign_employee_group: values.campaign_employee_group || null,
					to_staff: values.to_staff ? 1 : 0,
					to_students: values.to_students ? 1 : 0,
					to_guardians: values.to_guardians ? 1 : 0,
					to_community: values.to_community ? 1 : 0,
				},
			});
			const result = response?.message || {};
			const commName = String(result.communication || "").trim();
			if (!commName) throw new Error(__("Communication creation did not return a document name."));

			d.hide();
			frappe.show_alert({
				message: __(
					"Draft communication created for Morning Brief and archive. Opened for final review."
				),
				indicator: "green",
			});
			frappe.set_route("Form", "Org Communication", commName);
		} catch (error) {
			frappe.msgprint({
				title: __("Unable to create policy communication"),
				indicator: "red",
				message: (error && error.message) || __("Please review your inputs and try again."),
			});
		} finally {
			d.set_primary_action(__("Create Draft Communication"), submitAction);
			d.enable_primary_action();
		}
	};

	d = new frappe.ui.Dialog({
		title: __("Share Policy Amendment"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "context_html",
				options: `<div class="text-muted">
					<p><strong>${__("Policy Version")}</strong>: ${frappe.utils.escape_html(String(frm.doc.name || ""))}</p>
					<p><strong>${__("Institutional Policy")}</strong>: ${frappe.utils.escape_html(String(frm.doc.institutional_policy || ""))}</p>
					<p><strong>${__("Default schedule")}</strong>: ${__("1 week visibility (editable)")}</p>
				</div>`,
			},
			{
				fieldtype: "Data",
				fieldname: "title",
				label: __("Communication Title"),
				reqd: 1,
				default: defaultTitle,
			},
			{
				fieldtype: "Select",
				fieldname: "target_scope",
				label: __("Target Scope"),
				options: "Organization (All Schools)\nSchool\nTeam",
				default: defaultTargetScope(policyMeta),
				reqd: 1,
			},
			{
				fieldtype: "Link",
				fieldname: "target_school",
				label: __("School"),
				options: "School",
				default: String(policyMeta.policy_school || "").trim() || "",
				depends_on: "eval:doc.target_scope=='School'",
			},
			{
				fieldtype: "Link",
				fieldname: "target_team",
				label: __("Team"),
				options: "Team",
				depends_on: "eval:doc.target_scope=='Team'",
			},
			{
				fieldtype: "Section Break",
				fieldname: "recipient_section",
				label: __("Recipients"),
			},
			{
				fieldtype: "Check",
				fieldname: "to_staff",
				label: __("To Staff"),
				default: recipientDefaults.to_staff,
			},
			{
				fieldtype: "Check",
				fieldname: "to_students",
				label: __("To Students"),
				default: recipientDefaults.to_students,
			},
			{
				fieldtype: "Check",
				fieldname: "to_guardians",
				label: __("To Guardians"),
				default: recipientDefaults.to_guardians,
			},
			{
				fieldtype: "Check",
				fieldname: "to_community",
				label: __("To Community"),
				default: recipientDefaults.to_community,
			},
			{
				fieldtype: "Date",
				fieldname: "brief_start_date",
				label: __("Brief Start Date"),
				default: todayDate(),
				reqd: 1,
			},
			{
				fieldtype: "Date",
				fieldname: "brief_end_date",
				label: __("Brief End Date"),
				default: addDays(todayDate(), 6),
				reqd: 1,
			},
			{
				fieldtype: "Datetime",
				fieldname: "publish_from",
				label: __("Publish From"),
				default: frappe.datetime.now_datetime(),
			},
			{
				fieldtype: "Datetime",
				fieldname: "publish_to",
				label: __("Publish Until"),
			},
			{
				fieldtype: "Check",
				fieldname: "create_signature_campaign",
				label: __("Also create optional signature campaign"),
				default: 0,
			},
			{
				fieldtype: "Link",
				fieldname: "campaign_employee_group",
				label: __("Campaign Employee Group (optional)"),
				options: "Employee Group",
				depends_on: "eval:doc.create_signature_campaign==1",
			},
			{
				fieldtype: "Text Editor",
				fieldname: "message_html",
				label: __("Communication Content"),
				default: buildPolicyMessageHtml(frm, policyMeta),
			},
		],
		primary_action_label: __("Create Draft Communication"),
		primary_action: submitAction,
	});

	if (!isStaffPolicy) {
		d.set_df_property("create_signature_campaign", "read_only", 1);
		d.set_df_property(
			"create_signature_campaign",
			"description",
			__("Signature campaign is available only for Staff policies.")
		);
	}

	if (d.fields_dict.target_school) {
		d.fields_dict.target_school.get_query = () => {
			const organization = String(policyMeta.organization || "").trim();
			if (!organization) return {};
			return {
				filters: {
					organization,
				},
			};
		};
	}

	if (d.fields_dict.target_team) {
		d.fields_dict.target_team.get_query = () => {
			const organization = String(policyMeta.organization || "").trim();
			const scope = d.get_value("target_scope");
			const school = scope === "School" ? d.get_value("target_school") : null;
			const filters = {};
			if (organization) filters.organization = organization;
			if (school) filters.school = school;
			return { filters };
		};
	}

	d.show();
	const targetScopeField = d.get_field("target_scope");
	if (targetScopeField && targetScopeField.$input) {
		targetScopeField.$input.on("change", () => {
			const scope = d.get_value("target_scope");
			if (scope === "Team") {
				d.set_value("to_students", 0);
				d.set_value("to_guardians", 0);
				d.set_value("to_community", 0);
				d.set_value("to_staff", 1);
			}
		});
	}
}
