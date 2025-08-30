// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/students/doctype/referral_case/referral_case.js

frappe.ui.form.on("Referral Case", {
	refresh(frm) {
		// Primary: Add Entry
		frm.add_custom_button(__("Add Entry"), () => open_entry_dialog(frm), __("Actions"));

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

		// Assign case manager
		frm.add_custom_button(__("Assign Case Manager"), () => assign_manager_dialog(frm), __("Actions"));
	}
});

function quick_status(frm, new_status) {
	frappe.call({
		method: "ifitwala_ed.students.doctype.referral_case.referral_case.quick_update_status",
		args: { name: frm.doc.name, new_status },
		callback: () => frm.reload_doc()
	});
}

function assign_manager_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Assign Case Manager"),
		fields: [
			{ fieldname: "user", fieldtype: "Link", label: __("User"), options: "User", reqd: 1 }
		],
		primary_action_label: __("Assign"),
		primary_action: (v) => {
			d.hide();
			frappe.call({
				method: "ifitwala_ed.students.doctype.referral_case.referral_case.set_manager",
				args: { name: frm.doc.name, user: v.user },
				callback: () => frm.reload_doc()
			});
		}
	});
	d.show();
}

function open_entry_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("New Case Entry"),
		fields: [
			{ fieldname: "entry_type", fieldtype: "Select", label: __("Entry Type"),
				options: "Meeting\nCounseling Session\nAcademic Support\nCheck-in\nFamily Contact\nExternal Referral\nSafety Plan\nReview\nOther", reqd: 1 },
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
				callback: () => frm.reload_doc()
			});
		}
	});
	d.show();
}

