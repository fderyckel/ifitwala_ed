// Copyright (c) 2024, François de Ryckel 
// For license information, please see license.txt

// ifitwala_ed/students/doctype/student/student.js

frappe.ui.form.on("Student", {
	setup(frm) {
		// Keep: sibling picker filter
		frm.set_query("student", "siblings", (doc) => ({
			filters: { name: ["!=", doc.name] }
		}));
	},

	refresh(frm) {
		frappe.dynamic_link = { doc: frm.doc, fieldname: "name", doctype: "Student" };

		// Keep: load/clear address & contact, plus Student Contact button
		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);
			frappe
				.call({
					method: "ifitwala_ed.students.doctype.student.student.get_contact_linked_to_student",
					args: { student_name: frm.doc.name }
				})
				.then((r) => {
					if (r && r.message) {
						frm.add_custom_button(__("Student Contact"), () => {
							frappe.set_route("Form", "Contact", r.message);
						});
					}
				});
		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}

		// --- Support button (teacher-facing SSG pulled from Referral Case Entries) ---
		if (frm.is_new()) return;

		const canSeeSupport =
			frappe.user.has_role("Counselor") ||
			frappe.user.has_role("Academic Admin") ||
			frappe.user.has_role("System Manager") ||
			frappe.user.has_role("Instructor") ||
			frappe.user.has_role("Academic Staff");

		if (!canSeeSupport) return;

		// Avoid duplicates on soft refresh
		if (!frm.custom_buttons) frm.custom_buttons = {};
		if (!frm.custom_buttons.__support_btn) {
			const btn = frm.add_custom_button(__("Support"), () => open_support_modal(frm));
			// keep light blue styling
			btn.removeClass("btn-default btn-primary").addClass("btn-info");
			btn.find("span").prepend(frappe.utils.icon("book-open", "sm"));
			frm.custom_buttons.__support_btn = btn;
		}
	}
});

// --- New Support modal (no AY, no acknowledgements; lean teacher view) ---
async function open_support_modal(frm) {
	const student = frm.doc.name;
	if (!student) return;

	const d = new frappe.ui.Dialog({
		title: __("Student Support Guidance"),
		fields: [{ fieldname: "body", fieldtype: "HTML" }],
		size: "large",
		primary_action_label: __("Close"),
		primary_action: () => d.hide()
	});

	d.show();

	// Loading state
	const $body = d.get_field("body").$wrapper;
	$body.html(`<div class="p-3 text-muted small">${__("Loading published guidance…")}</div>`);

	try {
		const { message: rows } = await frappe.call({
			method: "ifitwala_ed.students.doctype.referral_case.referral_case.get_student_support_guidance",
			args: { student }
		});

		const items = Array.isArray(rows) ? rows : [];
		if (!items.length) {
			$body.html(`
				<div class="p-3 text-muted">${__("No published, open guidance found for this student.")}</div>
			`);
			return;
		}

		const html = `
			<div class="list-group" style="max-height:60vh; overflow:auto;">
				${items
					.map((r) => {
						const when = r.entry_datetime ? frappe.datetime.str_to_user(r.entry_datetime) : "";
						const caseName = r.case_name ? frappe.utils.escape_html(r.case_name) : "";
						const assignee = r.assignee ? frappe.utils.escape_html(r.assignee) : __("Unassigned");
						const author = r.author ? frappe.utils.escape_html(r.author) : "";
						const summary = r.summary || "";
						return `
							<div class="list-group-item">
								<div class="d-flex justify-content-between align-items-center">
									<div class="fw-semibold">${__("Student Support Guidance")}</div>
									<div class="text-muted small">${when}</div>
								</div>
								<div class="mt-1 small text-muted">
									${__("Case")}: <span class="fw-semibold">${caseName}</span> ·
									${__("Assignee")}: <span class="fw-semibold">${assignee}</span>
									${author ? ` · ${__("Author")}: <span class="fw-semibold">${author}</span>` : ""}
								</div>
								<div class="mt-2">${summary}</div>
							</div>
						`;
					})
					.join("")}
			</div>
		`;
		$body.html(html);
	} catch (e) {
		$body.html(`
			<div class="p-3 text-danger small">${__("Failed to load guidance or permission denied.")}</div>
		`);
		// eslint-disable-next-line no-console
		console.error(e);
	}
}
