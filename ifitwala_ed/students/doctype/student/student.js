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
		// enable dynamic linking for address/contact
		frappe.dynamic_link = { doc: frm.doc, fieldname: "name", doctype: "Student" };

		// Load or clear address & contact; add "Student Contact" button independently of Support
		if (!frm.is_new()) {
			frappe.contacts.render_address_and_contact(frm);
			frappe.call({
				method: "ifitwala_ed.students.doctype.student.student.get_contact_linked_to_student",
				args: { student_name: frm.doc.name }
			}).then((r) => {
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
			// keep a private handle; do NOT touch frm.custom_buttons
			if (frm.__ifitwala_support_btn) {
				try { frm.__ifitwala_support_btn.remove(); } catch (e) {}
				frm.__ifitwala_support_btn = null;
			}

			const canSeeSupport =
				frappe.user.has_role("Counselor") ||
				frappe.user.has_role("Academic Admin") ||
				frappe.user.has_role("System Manager") ||
				frappe.user.has_role("Instructor") ||
				frappe.user.has_role("Academic Staff");

			if (canSeeSupport) {
				frappe.call({
					method: "ifitwala_ed.students.doctype.referral_case.referral_case.card_open_published_guidance",
					args: { student: frm.doc.name }
				}).then((r) => {
					const n = (r && r.message && cint(r.message.value)) || 0;
					if (n > 0) {
						const btn = frm.add_custom_button(__("Support"), () => open_support_modal(frm));
						btn.removeClass("btn-default btn-primary").addClass("btn-info");
						btn.find("span").prepend(frappe.utils.icon("book-open", "sm"));
						frm.__ifitwala_support_btn = btn; // store only our own button
					}
				}).catch(() => {
					/* ignore permission/transient errors; do not affect other buttons */
				});
			}
		}
	}
});

// --- New Support modal (no AY, no acknowledgements; lean teacher view) ---
// --- Enhanced, BS4-friendly Support modal renderer ---
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

	// BS4 colors
	const infoBlue = "#17a2b8";

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

	// small inline SVG icons using frappe.utils.icon (feather)
	const icon = (name) => frappe.utils.icon(name, "sm");

	try {
		const { message: rows } = await frappe.call({
			method: "ifitwala_ed.students.doctype.referral_case.referral_case.get_student_support_guidance",
			args: { student }
		});

		const items = Array.isArray(rows) ? rows : [];
		if (!items.length) {
			$body.html(`
				<div class="p-3 text-muted">${__("No published, active guidance found for this student.")}</div>
			`);
			return;
		}

		const html = items.map((r) => {
			const when = r.entry_datetime ? neatDate(r.entry_datetime) : "";
			const assignee = r.assignee ? frappe.utils.escape_html(r.assignee) : __("All instructors");
			const authorName = r.author
				? frappe.utils.escape_html((frappe.user_info(r.author) || {}).fullname || r.author)
				: "";
			const summary = r.summary || "";
			const status = (r.status || "Open").trim();

			// status badge (only show if In Progress; keep Open implicit)
			const statusBadge =
				status === "In Progress"
					? `<span class="badge badge-success ml-2">${__("In Progress")}</span>`
					: "";

			// Triager-only case link
			const viewBtn = isTriager && r.case_name
				? `<button class="btn btn-sm btn-outline-primary ml-2" data-case="${frappe.utils.escape_html(r.case_name)}">
						${__("View Case")}
				   </button>`
				: "";

			return `
				<div class="card mb-3 shadow-sm" style="border-left: 4px solid ${infoBlue};">
					<div class="card-body">
						<div class="d-flex justify-content-between align-items-center">
							<div class="small text-muted">
								<span class="mr-1">${icon("calendar")}</span>
								<strong>${when}</strong>
								${statusBadge}
							</div>
							${viewBtn}
						</div>

						<div class="mt-2 small text-muted">
							<span class="mr-1">${icon("user")}</span>${__("Assignee")}: <strong>${assignee}</strong>
							${authorName ? ` · <span class="mr-1 ml-1">${icon("edit-3")}</span>${__("Author")}: <strong>${authorName}</strong>` : ""}
						</div>

						<div class="mt-3">
							<span class="mr-1 text-info">${icon("book-open")}</span>
							<span>${summary}</span>
						</div>
					</div>
				</div>
			`;
		}).join("");

		$body.html(`<div>${html}</div>`);

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
