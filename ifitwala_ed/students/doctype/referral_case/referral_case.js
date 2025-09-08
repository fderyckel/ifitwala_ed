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

		// Promote to Guidance (standalone, primary color, with icon)
		const promoBtn = frm.add_custom_button(__("Promote to Guidance"), () => open_promote_dialog(frm));
		promoBtn.removeClass("btn-default").addClass("btn-primary");
		promoBtn.find("span").prepend(frappe.utils.icon("send", "sm"));

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

// Keep: add entry dialog
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
			}).then(() => {
				frappe.show_alert({ message: __("Entry added"), indicator: "green" });
				return frm.reload_doc();
			});
		}
	});
	d.show();
}

// Promote-to-Guidance client dialog
function open_promote_dialog(frm) {
	const entries = (frm.doc.entries || []);
	if (!entries.length) {
		frappe.msgprint({ message: __("Add at least one entry before promoting guidance."), indicator: "orange" });
		return;
	}

	const lines = entries.map(row => {
		const dt = row.entry_datetime || row.creation || "";
		const typ = row.entry_type || "—";
		const tmp = document.createElement("div");
		tmp.innerHTML = row.summary || "";
		const plain = (tmp.textContent || tmp.innerText || "").trim();
		const preview = plain.length > 80 ? (plain.slice(0, 77) + "…") : plain || "—";
		const label = `${dt ? `${dt} • ` : ""}${typ} • ${preview}`;
		return { label, value: row.name };
	});

	const d = new frappe.ui.Dialog({
		title: __("Promote to Guidance"),
		fields: [
			{ fieldname: "entry_rowname", fieldtype: "Select", label: __("Source Entry"), options: lines.map(x => x.label).join("\n"), reqd: 1 },
			{ fieldname: "item_type", fieldtype: "Select", label: __("Item Type"),
				options: "Accommodation\nStrategy\nTrigger\nSafety Alert\nFYI", reqd: 1, default: "Strategy" },
			{ fieldname: "teacher_text", fieldtype: "Text Editor", label: __("Teacher-facing Text"), reqd: 1 },
			{ fieldname: "confidentiality", fieldtype: "Select", label: __("Visibility"),
				options: "Teachers-of-student\nCase team only", default: "Teachers-of-student", reqd: 1 },
			{ fieldname: "high_priority", fieldtype: "Check", label: __("High Priority") },
			{ fieldname: "requires_ack", fieldtype: "Check", label: __("Require Teacher Acknowledgment"), default: 1 },
			{ fieldname: "effective_from", fieldtype: "Date", label: __("Effective From") },
			{ fieldname: "expires_on", fieldtype: "Date", label: __("Expires On") },
			{ fieldname: "publish", fieldtype: "Check", label: __("Publish Now (update snapshot, notify)"), default: 1 },
		],
		primary_action_label: __("Publish"),
		primary_action: async (v) => {
			const hit = lines.find(x => x.label === v.entry_rowname);
			if (!hit) {
				frappe.msgprint({ message: __("Select a source entry."), indicator: "orange" });
				return;
			}
			d.hide();
			await frappe.call({
				method: "ifitwala_ed.students.doctype.referral_case.referral_case.promote_entry_to_guidance",
				args: {
					case_name: frm.doc.name,
					entry_rowname: hit.value,
					item_type: v.item_type,
					teacher_text: v.teacher_text,
					high_priority: v.high_priority ? 1 : 0,
					requires_ack: v.requires_ack ? 1 : 0,
					effective_from: v.effective_from || null,
					expires_on: v.expires_on || null,
					confidentiality: v.confidentiality,
					publish: v.publish ? 1 : 0
				}
			}).then(r => {
				frappe.show_alert({ message: __("Guidance published"), indicator: "green" });
				const ssg = r && r.message && r.message.support_guidance;
				if (ssg) {
					frappe.msgprint({
						title: __("Published"),
						message: __("View the teacher-facing record: {0}", [`<a href="#Form/Student Support Guidance/${frappe.utils.escape_html(ssg)}">${frappe.utils.escape_html(ssg)}</a>`]),
						indicator: "green"
					});
				}
			});
		}
	});

	// Pre-fill teacher_text from the first entry
	d.set_value("entry_rowname", lines[0].label);
	const first = entries[0];
	const tmp = document.createElement("div");
	tmp.innerHTML = first.summary || "";
	const plain = (tmp.textContent || tmp.innerText || "").trim();
	d.set_value("teacher_text", plain);

	// Sync preview when selection changes
	d.fields_dict.entry_rowname.df.onchange = () => {
		const label = d.get_value("entry_rowname");
		const sel = lines.find(x => x.label === label);
		if (!sel) return;
		const row = entries.find(r => r.name === sel.value);
		const el = document.createElement("div");
		el.innerHTML = (row && row.summary) || "";
		const p = (el.textContent || el.innerText || "").trim();
		if (p) d.set_value("teacher_text", p);
	};

	d.show();
}
