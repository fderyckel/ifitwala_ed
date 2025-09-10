// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/students/doctype/referral_case/referral_case.js

frappe.ui.form.on("Referral Case", {
	refresh(frm) {
		// Limit 'case_manager' field choices to Counselor or Academic Admin
		frm.set_query("case_manager", () => ({
			query: "ifitwala_ed.students.doctype.referral_case.referral_case.users_with_role",
			filters: { roles: ["Counselor", "Academic Admin"] }
		}));

		// Primary: Add Entry (standalone, colored, with icon)
		const addBtn = frm.add_custom_button(__("Add Entry"), () => open_entry_dialog(frm)); // no group ⇒ not nested
		addBtn.removeClass("btn-default").addClass("btn-success");
		addBtn.find("span").prepend(frappe.utils.icon("add", "sm"));

		// ⬇️ Removed: “Promote to Guidance” flow (SSG is retired)

		// Case status quick-actions
		const st = (frm.doc.case_status || "Open").trim();
		if (st === "Open") {
			frm.add_custom_button(__("Start Work"), () => quick_status(frm, "In Progress"), __("Status"));
			frm.add_custom_button(__("On Hold"), () => quick_status(frm, "On Hold"), __("Status"));
			frm.add_custom_button(__("Close Case"), () => quick_status(frm, "Closed"), __("Status"));
		} else if (st === "In Progress") {
			frm.add_custom_button(__("On Hold"), () => quick_status(frm, "On Hold"), __("Status"));
			frm.add_custom_button(__("Close Case"), () => quick_status(frm, "Closed"), __("Status"));
		} else if (st === "On Hold") {
			frm.add_custom_button(__("Resume Work"), () => quick_status(frm, "In Progress"), __("Status"));
			frm.add_custom_button(__("Close Case"), () => quick_status(frm, "Closed"), __("Status"));
		} else if (st === "Escalated") {
			frm.add_custom_button(__("Start Work"), () => quick_status(frm, "In Progress"), __("Status"));
			frm.add_custom_button(__("Close Case"), () => quick_status(frm, "Closed"), __("Status"));
		} else if (st === "Closed") {
			frm.add_custom_button(__("Reopen Case"), () => quick_status(frm, "In Progress"), __("Status"));
		}

		// NOTE: No "Assign Case Manager", "Escalate", or "Mark Mandated Reporting" buttons.
		// Triage staff edit the Case fields directly. Server will log timeline entries.

		// Limit child-table assignee (grid picker) to Academic Staff
		if (frm.fields_dict.entries && frm.fields_dict.entries.grid) {
			frm.fields_dict.entries.grid.get_field("assignee").get_query = () => ({
				query: "ifitwala_ed.students.doctype.referral_case.referral_case.users_with_role",
				filters: { roles: ["Academic Staff"] }
			});
		}

		// Friendly banner for triage roles
		const canTriage = frappe.user.has_role(["Counselor", "Academic Admin"]);
		if (canTriage && frm.doc.docstatus === 1) {
			frm.dashboard.set_headline(__(
				"Edit <b>Severity</b>, <b>Mandated Reporting</b>, and <b>Case Manager</b> in the form. " +
				"Changes are logged to this case and mirrored on the originating Student Referral."
			));
		}
	}
});

function quick_status(frm, new_status) {
	frappe.call({
		method: "ifitwala_ed.students.doctype.referral_case.referral_case.quick_update_status",
		args: { name: frm.doc.name, new_status }
	}).then(() => {
		frappe.show_alert({ message: __("Status updated"), indicator: "green" });
		return frm.reload_doc();
	});
}

// Keep: add entry dialog (now includes “Student Support Guidance”)
function open_entry_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("New Case Entry"),
		fields: [
			{ fieldname: "entry_type", fieldtype: "Select", label: __("Entry Type"),
				options: "Meeting\nCounseling Session\nAcademic Support\nCheck-in\nFamily Contact\nExternal Referral\nSafety Plan\nReview\nOther\nStudent Support Guidance", reqd: 1 },
			{ fieldname: "summary", fieldtype: "Text Editor", label: __("Summary"), reqd: 1 },
			{ fieldname: "assignee", fieldtype: "Link", label: __("Assignee (optional)"), options: "User" },
			{ fieldname: "status", fieldtype: "Select", label: __("Status"), options: "Open\nIn Progress\nDone\nCancelled", default: "Open" },
			{ fieldname: "attachment", fieldtype: "Attach", label: __("Attachment") },
			{ fieldname: "create_todo", fieldtype: "Check", label: __("Create ToDo for Assignee"), default: 1 },
			{ fieldname: "due_date", fieldtype: "Date", label: __("Due Date (ToDo)") }
		],
		primary_action_label: __("Add"),
		primary_action: (v) => {
			d.hide();
			frappe.call({
				method: "ifitwala_ed.students.doctype.referral_case.referral_case.add_entry",
				args: {
					name: frm.doc.name,
					entry_type: v.entry_type,
					summary: v.summary,
					assignee: v.assignee || null,
					status: v.status || "Open",
					attachment: v.attachment || null,
					create_todo: v.create_todo ? 1 : 0,
					due_date: v.due_date || null
				},
			}).then(() => {
				frappe.show_alert({ message: __("Entry added"), indicator: "green" });
				return frm.reload_doc();
			});
		}
	});
	d.show();
}

// ⬇️ Removed the open_promote_dialog(...) function completely (SSG retired)
