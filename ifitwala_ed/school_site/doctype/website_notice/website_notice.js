// ifitwala_ed/school_site/doctype/website_notice/website_notice.js

const WORKFLOW_METHOD =
	"ifitwala_ed.school_site.doctype.website_notice.website_notice.transition_workflow_state";

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

frappe.ui.form.on("Website Notice", {
	refresh(frm) {
		frm.clear_custom_buttons();
		getWorkflowActions(frm).forEach((actionConfig) => {
			frm.add_custom_button(
				actionConfig.label,
				() => runWorkflowAction(frm, actionConfig),
				__("Workflow")
			);
		});

		if (frm.dashboard && frm.dashboard.set_headline) {
			const banners = [];
			if (!frm.doc.content_owner) {
				banners.push(__("Set a Content Owner so alert ownership is clear."));
			}
			if (frm.doc.workflow_state === "Published" && frm.doc.publish_at) {
				banners.push(__("This notice is scheduled and will only go live after Publish At."));
			}
			if (frm.doc.workflow_state === "Published" && frm.doc.expire_at) {
				banners.push(__("This notice will automatically return to draft after Expire At."));
			}
			if (!frm.doc.school) {
				banners.push(__("Select a School before publishing this notice."));
			}

			if (banners.length) {
				const html = banners.map((msg) => `• ${frappe.utils.escape_html(msg)}`).join("<br>");
				frm.dashboard.set_headline(`<span class="text-warning">${html}</span>`);
			} else {
				frm.dashboard.set_headline("");
			}
		}
	}
});
