// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/curriculum/doctype/lesson/lesson.js

frappe.ui.form.on("Lesson", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.name) return;

		// Keep your existing custom buttons here, if any.

		// Preview (staff-only preview mode on portal)
		frm.add_custom_button(__("Preview as Student"), () => {
			if (!frm.doc.slug) {
				frappe.msgprint(__("Please save to generate a slug first."));
				return;
			}
			const url = `/sp/lms/lesson?slug=${encodeURIComponent(frm.doc.slug)}&preview=1`;
			window.open(url, "_blank");
		}, __("Actions"));

		// Activities: read-only ordered list
		frm.add_custom_button(__("View Activities (ordered)"), async () => {
			const rows = await fetch_activities(frm.doc.name);
			show_activities_dialog(rows);
		}, __("Activities"));

		// Activities: reorder (bulk save on server)
		frm.add_custom_button(__("Reorder Activities"), async () => {
			const rows = await fetch_activities(frm.doc.name);
			show_reorder_dialog(frm, rows);
		}, __("Activities"));
	}
});

// ---- helpers ----

async function fetch_activities(lesson_name) {
	// Lean client fetch; sorted by `order` then idx/title as tie-breakers.
	const rows = await frappe.db.get_list("Lesson Activity", {
		fields: ["name", "activity_type", "title", "order"],
		filters: { parent: lesson_name, parenttype: "Lesson", parentfield: "activities" },
		order_by: "`order` asc, idx asc",
		limit: 1000
	});
	return (rows || []).map(r => ({
		name: r.name,
		title: r.title || "(Untitled)",
		activity_type: r.activity_type || "",
		order: Number.isFinite(+r.order) ? +r.order : 0
	}));
}

function show_activities_dialog(rows) {
	const d = new frappe.ui.Dialog({
		title: __("Activities (ordered)"),
		size: "large"
	});

	const list = (rows || []).map(r => {
		const orderBadge = `<span class="badge bg-secondary me-2">${r.order || "-"}</span>`;
		const typeBadge = r.activity_type
			? `<span class="badge bg-light text-muted ms-2">${frappe.utils.escape_html(r.activity_type)}</span>`
			: "";
		const title = `<span>${frappe.utils.escape_html(r.title)}</span>`;
		return `<li class="list-group-item d-flex align-items-center justify-content-between">
			<div>${orderBadge}${title}${typeBadge}</div>
		</li>`;
	}).join("");

	d.set_message(`
		<div class="mb-2 text-muted small">
			${__("Sorted by")} <code>order</code>.
		</div>
		<ul class="list-group">${list || `<li class="list-group-item">${__("No activities yet.")}</li>`}</ul>
	`);

	d.set_primary_action(__("Close"), () => d.hide());
	d.show();
}

function show_reorder_dialog(frm, initialRows) {
	let rows = [...(initialRows || [])];

	const d = new frappe.ui.Dialog({
		title: __("Reorder Activities"),
		size: "large",
		primary_action_label: __("Save Order"),
		primary_action: async () => {
			try {
				await save_activity_order_server(frm.doc.name, rows);
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
		const items = rows.map((r, idx) => {
			return `
			<li class="list-group-item d-flex align-items-center justify-content-between" data-idx="${idx}">
				<div class="d-flex align-items-center">
					<span class="text-muted me-2">${(idx + 1) * 10}</span>
					<strong>${frappe.utils.escape_html(r.title)}</strong>
					${r.activity_type ? `<span class="badge bg-light text-muted ms-2">${frappe.utils.escape_html(r.activity_type)}</span>` : ""}
				</div>
				<div class="btn-group btn-group-sm" role="group">
					<button type="button" class="btn btn-outline-secondary btn-up" ${idx === 0 ? "disabled" : ""}>↑</button>
					<button type="button" class="btn btn-outline-secondary btn-down" ${idx === rows.length - 1 ? "disabled" : ""}>↓</button>
				</div>
			</li>`;
		}).join("");

		d.set_message(`
			<div class="mb-2 text-muted small">
				${__("Use the arrows to move items. New")} <code>order</code> ${__("will be set to 10,20,30…")}
			</div>
			<ul class="list-group" id="reorder-activities">
				${items || `<li class="list-group-item">${__("No activities to reorder.")}</li>`}
			</ul>
		`);

		const $list = d.$wrapper.find("#reorder-activities");
		$list.off("click");
		$list.on("click", ".btn-up, .btn-down", function () {
			const $li = $(this).closest("li");
			const idx = parseInt($li.attr("data-idx"), 10);
			if ($(this).hasClass("btn-up") && idx > 0) {
				[rows[idx - 1], rows[idx]] = [rows[idx], rows[idx - 1]];
			}
			if ($(this).hasClass("btn-down") && idx < rows.length - 1) {
				[rows[idx + 1], rows[idx]] = [rows[idx], rows[idx + 1]];
			}
			render_list();
		});
	}

	render_list();
	d.show();
}

async function save_activity_order_server(lesson_name, rows) {
	const activity_names = rows.map(r => r.name);
	const res = await frappe.call({
		method: "ifitwala_ed.curriculum.doctype.lesson_activity.lesson_activity.reorder_lesson_activities",
		args: { lesson: lesson_name, activity_names },
		freeze: true,
		freeze_message: __("Updating order…")
	});
	return res && res.message;
}
