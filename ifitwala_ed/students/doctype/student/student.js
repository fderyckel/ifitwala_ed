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

		// --- Support button (only if there are open, published SSG entries) ---
		if (!frm.is_new()) {
			const canSeeSupport =
				frappe.user.has_role("Counselor") ||
				frappe.user.has_role("Academic Admin") ||
				frappe.user.has_role("System Manager") ||
				frappe.user.has_role("Instructor") ||
				frappe.user.has_role("Academic Staff");

			// Remove any prior button to avoid stale UI on role/date changes
			if (!frm.custom_buttons) frm.custom_buttons = {};
			if (frm.custom_buttons.__support_btn) {
				try { frm.custom_buttons.__support_btn.remove(); } catch (e) {}
				delete frm.custom_buttons.__support_btn;
			}

			if (canSeeSupport) {
				frappe
					.call({
						method:
							"ifitwala_ed.students.doctype.referral_case.referral_case.count_open_published_guidance",
						args: { student: frm.doc.name }
					})
					.then((r) => {
						const n = (r && r.message && cint(r.message.value)) || 0;
						if (n > 0) {
							const btn = frm.add_custom_button(__("Support"), () => open_support_modal(frm));
							btn.removeClass("btn-default btn-primary").addClass("btn-info");
							btn.find("span").prepend(frappe.utils.icon("book-open", "sm"));
							frm.custom_buttons.__support_btn = btn;
						}
					})
					.catch(() => {
						// silently ignore (permissions or transient error)
					});
			}
		}

	}
});

// --- New Support modal (no AY, no acknowledgements; lean teacher view) ---
async function open_support_modal(frm) {
	const student = frm.doc.name;
	if (!student) return;

	const isTriager =
		frappe.user.has_role("Counselor") ||
		frappe.user.has_role("Academic Admin") ||
		frappe.user.has_role("System Manager");

	const d = new frappe.ui.Dialog({
		title: __("Student Support Guidance"),
		fields: [{ fieldname: "body", fieldtype: "HTML" }],
		size: "large",
		primary_action_label: __("Close"),
		primary_action: () => d.hide()
	});

	d.show();

	const $body = d.get_field("body").$wrapper;
	$body.html(`<div class="p-3 text-muted small">${__("Loading published guidance…")}</div>`);

	// helper: format to "09 September 2025"
	const neatDate = (dt) => {
		try {
			const o = frappe.datetime.str_to_obj(dt);
			return o
				? o.toLocaleDateString(undefined, { day: "2-digit", month: "long", year: "numeric" })
				: "";
		} catch {
			return "";
		}
	};

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
						const when = r.entry_datetime ? neatDate(r.entry_datetime) : "";
						const assignee =
							r.assignee ? frappe.utils.escape_html(r.assignee) : __("All instructors");
						const authorName = r.author
							? frappe.utils.escape_html((frappe.user_info(r.author) || {}).fullname || r.author)
							: "";
						const summary = r.summary || "";

						// For triagers, optionally show a subtle inline "View Case" button (kept)
						const viewBtn = isTriager && r.case_name
							? `<button class="btn btn-sm btn-outline-secondary ms-2" data-case="${frappe.utils.escape_html(r.case_name)}">
									${__("View Case")}
							   </button>`
							: "";

						return `
							<div class="list-group-item">
								<div class="d-flex justify-content-between align-items-center">
									<div class="text-muted small">${when}</div>
									${viewBtn}
								</div>
								<div class="mt-1 small text-muted">
									${__("Assignee")}: <span class="fw-semibold">${assignee}</span>
									${authorName ? ` · ${__("Author")}: <span class="fw-semibold">${authorName}</span>` : ""}
								</div>
								<div class="mt-2">${summary}</div>
							</div>
						`;
					})
					.join("")}
			</div>
		`;
		$body.html(html);

		// Wire View Case (triage users only)
		if (isTriager) {
			$body.on("click", "button[data-case]", (e) => {
				const cn = e.currentTarget.getAttribute("data-case");
				if (cn) {
					d.hide();
					frappe.set_route("Form", "Referral Case", cn);
				}
			});
		}
	} catch (e) {
		$body.html(`
			<div class="p-3 text-danger small">${__("Failed to load guidance or permission denied.")}</div>
		`);
		// eslint-disable-next-line no-console
		console.error(e);
	}
}
