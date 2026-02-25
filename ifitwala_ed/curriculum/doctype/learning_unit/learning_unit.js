// Copyright (c) 2024, fdR and contributors
// For license information, please see license.txt

// ifitwala_ed/curriculum/doctype/learning_unit/learning_unit.js


frappe.ui.form.on("Learning Unit", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.name) return;

		// --- Lessons menu ---
		frm.add_custom_button(__("View Lessons (ordered)"), async () => {
			const rows = await fetch_lessons(frm.doc.name);
			show_lessons_dialog(rows);
		}, __("Lessons"));

		frm.add_custom_button(__("Reorder Lessons"), async () => {
			const rows = await fetch_lessons(frm.doc.name);
			show_reorder_dialog(frm, rows);
		}, __("Lessons"));

		// NEW: Add a lesson (opens new tab with fields prefilled)
		frm.add_custom_button(__("Add a lesson"), () => {
			if (!frm.doc.course) {
				frappe.msgprint(__("Please set a Course on this Learning Unit first."));
				return;
			}
			// Prefill via route options (works across tabs)
			frappe.utils.set_route_options({
				course: frm.doc.course,
				learning_unit: frm.doc.name,
			});
			// open the "New Lesson" form in a new tab
			window.open("/desk/lesson/new-lesson", "_blank");
		}, __("Lessons"));

		// Make the Lessons group button blue (primary)
		frm.page.set_inner_btn_group_as_primary(__("Lessons"));
	}
});

// ---- helpers ----

async function fetch_lessons(unit_name) {
	// Lean client fetch; sorted by lesson_order then title.
	const rows = await frappe.db.get_list("Lesson", {
		fields: ["name", "title", "lesson_order", "lesson_type", "is_published"],
		filters: { learning_unit: unit_name },
		order_by: "lesson_order asc, title asc",
		limit: 1000
	});
	return (rows || []).map(r => ({
		name: r.name,
		title: r.title || "(Untitled)",
		lesson_order: Number.isFinite(+r.lesson_order) ? +r.lesson_order : 0,
		lesson_type: r.lesson_type || "",
		is_published: !!r.is_published
	}));
}


function show_lessons_dialog(rows) {
	const d = new frappe.ui.Dialog({
		title: __("Lessons (ordered)"),
		size: "large",
		fields: [{ fieldtype: "HTML", fieldname: "body" }]
	});

	const list = (rows || []).map(r => {
		const orderBadge = `<span class="badge bg-secondary me-2">${r.lesson_order || "-"}</span>`;
		const typeBadge = r.lesson_type
			? `<span class="badge bg-light text-muted ms-2">${frappe.utils.escape_html(r.lesson_type)}</span>`
			: "";
		const pubDot = r.is_published
			? `<span class="indicator-pill green ms-2">${__("Published")}</span>`
			: `<span class="indicator-pill orange ms-2">${__("Draft")}</span>`;
		const link = `<a href="/desk/lesson/${encodeURIComponent(r.name)}" target="_blank">${frappe.utils.escape_html(r.title || "(Untitled)")}</a>`;
		return `<li class="list-group-item d-flex align-items-center justify-content-between">
			<div>${orderBadge}${link}${typeBadge}${pubDot}</div>
		</li>`;
	}).join("");

	const html = `
		<div class="mb-2 text-muted small">
			${__("Sorted by")} <code>lesson_order</code> ${__("then")} <code>title</code>.
		</div>
		<ul class="list-group">
			${list || `<li class="list-group-item">${__("No lessons yet.")}</li>`}
		</ul>
	`;

	d.get_field("body").$wrapper.html(html);
	d.set_primary_action(__("Close"), () => d.hide());
	d.show();
}

function show_reorder_dialog(frm, initialRows) {
	let rows = [...(initialRows || [])];

	const d = new frappe.ui.Dialog({
		title: __("Reorder Lessons"),
		size: "large",
		primary_action_label: __("Save Order"),
		fields: [{ fieldtype: "HTML", fieldname: "body" }],
		primary_action: async () => {
			try {
				await save_lesson_order_server(frm.doc.name, rows);
				d.hide();
				frappe.show_alert({ message: __("Order updated"), indicator: "green" });
				frm.reload_doc();
			} catch (err) {
				console.error(err);
				frappe.msgprint({
					title: __("Reorder failed"),
					message: __(err && err.message ? err.message : "An error occurred."),
					indicator: "red"
				});
			}
		}
	});

	function render_list() {
		const items = rows.map((r, idx) => `
			<li class="list-group-item d-flex align-items-center justify-content-between" data-idx="${idx}">
				<div class="d-flex align-items-center">
					<span class="text-muted me-2">${(idx + 1) * 10}</span>
					<strong>${frappe.utils.escape_html(r.title || "(Untitled)")}</strong>
				</div>
				<div class="btn-group btn-group-sm" role="group">
					<button type="button" class="btn btn-outline-secondary btn-up" ${idx === 0 ? "disabled" : ""}>↑</button>
					<button type="button" class="btn btn-outline-secondary btn-down" ${idx === rows.length - 1 ? "disabled" : ""}>↓</button>
				</div>
			</li>
		`).join("");

		const html = `
			<div class="mb-2 text-muted small">
				${__("Use the arrows to move items. New")} <code>lesson_order</code> ${__("will be set to 10,20,30…")}
			</div>
			<ul class="list-group" id="reorder-lessons">
				${items || `<li class="list-group-item">${__("No lessons to reorder.")}</li>`}
			</ul>
		`;

		d.get_field("body").$wrapper.html(html);

		const $list = d.$wrapper.find("#reorder-lessons");
		$list.off("click");
		$list.on("click", ".btn-up, .btn-down", function () {
			const $li = $(this).closest("li");
			const idx = parseInt($li.attr("data-idx"), 10);
			if ($(this).hasClass("btn-up") && idx > 0) [rows[idx - 1], rows[idx]] = [rows[idx], rows[idx - 1]];
			if ($(this).hasClass("btn-down") && idx < rows.length - 1) [rows[idx + 1], rows[idx]] = [rows[idx], rows[idx + 1]];
			render_list();
		});
	}

	render_list();
	d.show();
}


async function save_lesson_order_server(learning_unit_name, rows) {
	const lesson_names = rows.map(r => r.name);
	const res = await frappe.call({
		method: "ifitwala_ed.curriculum.doctype.lesson.lesson.reorder_lessons",
		args: { learning_unit: learning_unit_name, lesson_names },
		freeze: true,
		freeze_message: __("Updating order…")
	});
	return res && res.message;
}
