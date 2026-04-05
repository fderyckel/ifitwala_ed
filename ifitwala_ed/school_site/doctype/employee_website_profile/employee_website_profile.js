// ifitwala_ed/school_site/doctype/employee_website_profile/employee_website_profile.js

const WORKFLOW_METHOD =
	"ifitwala_ed.school_site.doctype.employee_website_profile.employee_website_profile.transition_workflow_state";

function userHasAnyRole(roles) {
	if (!Array.isArray(roles) || !roles.length) return false;
	return roles.some((role) => frappe.user.has_role(role));
}

function getWorkflowState(frm) {
	const state = String(frm.doc.workflow_state || "").trim();
	return state || "Draft";
}

function getWorkflowActions(frm) {
	const state = getWorkflowState(frm);
	const canMarketing = userHasAnyRole(["Marketing User", "Website Manager", "System Manager"]);
	const canManager = userHasAnyRole(["Website Manager", "System Manager"]);
	const actions = [];

	if (state === "Draft" && canMarketing) {
		actions.push({ action: "request_review", label: __("Request Review") });
	}
	if (state === "In Review" && canManager) {
		actions.push({ action: "approve", label: __("Approve") });
	}
	if (state === "Approved" && canManager) {
		actions.push({ action: "publish", label: __("Publish") });
	}
	if (["In Review", "Approved", "Published"].includes(state) && canMarketing) {
		actions.push({ action: "return_to_draft", label: __("Return to Draft") });
	}
	return actions;
}

async function runWorkflowAction(frm, actionConfig) {
	if (frm.is_new()) {
		frappe.msgprint(__("Save the document before running workflow actions."));
		return;
	}

	try {
		await frappe.call({
			method: WORKFLOW_METHOD,
			args: {
				name: frm.doc.name,
				action: actionConfig.action
			},
			freeze: true
		});
		frappe.show_alert({
			message: __("Workflow updated: {0}", [actionConfig.label]),
			indicator: "green"
		});
		await frm.reload_doc();
	} catch (err) {
		// Server-side validation already surfaces the actionable message.
	}
}

async function syncSchoolFromEmployee(frm) {
	if (!frm.doc.employee) {
		return;
	}

	const res = await frappe.db.get_value("Employee", frm.doc.employee, "school");
	const employeeSchool = res && res.message ? res.message.school : null;
	if (employeeSchool && frm.doc.school !== employeeSchool) {
		await frm.set_value("school", employeeSchool);
	}
}

frappe.ui.form.on("Employee Website Profile", {
	refresh(frm) {
		frm.clear_custom_buttons();
		frm.set_df_property(
			"public_email",
			"description",
			__("Optional public-facing email. Leave blank to hide email from website people surfaces.")
		);
		frm.set_df_property(
			"public_phone",
			"description",
			__("Optional public-facing phone number. Leave blank to hide phone from website people surfaces.")
		);

		for (const action of getWorkflowActions(frm)) {
			frm.add_custom_button(action.label, () => runWorkflowAction(frm, action), __("Workflow"));
		}
	},

	employee(frm) {
		syncSchoolFromEmployee(frm);
	}
});
