// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/students/doctype/student_log_follow_up/student_log_follow_up.js

frappe.ui.form.on("Student Log Follow Up", {
	onload(frm) {
		// Set follow_up_author once (mirror current user full name)
		if (!frm.doc.follow_up_author) {
			frappe.call({
				method: "ifitwala_ed.students.doctype.student_log.student_log.get_employee_data",
				callback(r) {
					if (r && r.message && r.message.employee_full_name) {
						frm.set_value("follow_up_author", r.message.employee_full_name);
					}
				}
			});
		}

		// Ensure date exists
		if (!frm.doc.date) {
			frm.set_value("date", frappe.datetime.get_today());
		}
	},

	refresh(frm) {
		// Avoid duplicate buttons on rerender
		frm.clear_custom_buttons();

		// Safety: if author still blank (rare), fill once
		if (!frm.doc.follow_up_author) {
			frappe.call({
				method: "ifitwala_ed.students.doctype.student_log.student_log.get_employee_data",
				callback(r) {
					if (r && r.message && r.message.employee_full_name) {
						frm.set_value("follow_up_author", r.message.employee_full_name);
					}
				}
			});
		}

		// Ensure date exists
		if (!frm.doc.date) {
			frm.set_value("date", frappe.datetime.get_today());
		}

		// Quick navigation to parent Student Log
		if (frm.doc.student_log) {
			frm.add_custom_button(__("Open Student Log"), () => {
				frappe.set_route("Form", "Student Log", frm.doc.student_log);
			});
			frm.add_custom_button(__("View Evidence"), () => {
				open_student_log_evidence_dialog(frm);
			});
		}
	}
});

function open_student_log_evidence_dialog(frm) {
	if (!frm.doc.student_log) return;

	frappe.call({
		method: "ifitwala_ed.api.student_log_attachments.get_student_log_attachments",
		args: {
			student_log: frm.doc.student_log,
			audience: "staff",
		},
		callback(r) {
			const rows = (r.message && r.message.attachments) || [];
			const body = rows.length
				? rows.map(row => evidence_row_html(row)).join("")
				: `<p class="text-muted">${__("No evidence attachments on this Student Log.")}</p>`;

			frappe.msgprint({
				title: __("Student Log Evidence"),
				indicator: rows.length ? "blue" : "gray",
				message: `<div class="student-log-evidence-dialog">${body}</div>`,
				wide: true,
			});
		}
	});
}

function evidence_row_html(row) {
	const title = escape_html(row.title || row.file_name || row.external_url || row.row_name || __("Evidence"));
	const description = row.description ? `<div class="text-muted small">${escape_html(row.description)}</div>` : "";
	const meta = row.file_name ? `<div class="text-muted small">${escape_html(row.file_name)}</div>` : "";
	const href = escape_attr(row.open_url || row.external_url || "");
	const action = href
		? `<a class="btn btn-xs btn-default" href="${href}" target="_blank" rel="noreferrer">${__("Open")}</a>`
		: "";
	return `
		<div class="mb-3 rounded border p-3">
			<div class="d-flex justify-content-between gap-3">
				<div>
					<div class="font-weight-bold">${title}</div>
					${meta}
					${description}
				</div>
				<div>${action}</div>
			</div>
		</div>
	`;
}

function escape_html(value) {
	if (frappe.utils && frappe.utils.escape_html) {
		return frappe.utils.escape_html(String(value || ""));
	}
	return String(value || "")
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#039;");
}

function escape_attr(value) {
	return escape_html(value);
}
