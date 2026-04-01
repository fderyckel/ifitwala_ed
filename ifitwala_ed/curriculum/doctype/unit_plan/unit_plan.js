// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Unit Plan", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.name) return;

		frm.add_custom_button(__("View Lessons (ordered)"), async () => {
			const rows = await fetch_lessons(frm.doc.name);
			show_lessons_dialog(rows);
		}, __("Lessons"));

		frm.add_custom_button(__("Reorder Lessons"), async () => {
			const rows = await fetch_lessons(frm.doc.name);
			show_reorder_dialog(frm, rows);
		}, __("Lessons"));

		frm.add_custom_button(__("Add a lesson"), () => {
			if (!frm.doc.course) {
				frappe.msgprint(__("Please set a Course on this Unit Plan first."));
				return;
			}
			frappe.utils.set_route_options({
				course: frm.doc.course,
				unit_plan: frm.doc.name,
			});
			window.open("/desk/lesson/new-lesson", "_blank");
		}, __("Lessons"));

		frm.page.set_inner_btn_group_as_primary(__("Lessons"));
	},
});

async function fetch_lessons(unitPlan) {
	const rows = await frappe.db.get_list("Lesson", {
		fields: ["name", "title", "lesson_order", "lesson_type", "is_published"],
		filters: { unit_plan: unitPlan },
		order_by: "lesson_order asc, title asc",
		limit: 1000,
	});
	return (rows || []).map((row) => ({
		name: row.name,
		title: row.title || "(Untitled)",
		lesson_order: Number.isFinite(+row.lesson_order) ? +row.lesson_order : 0,
		lesson_type: row.lesson_type || "",
		is_published: !!row.is_published,
	}));
}

function show_lessons_dialog(rows) {
	const dialog = new frappe.ui.Dialog({
		title: __("Lessons (ordered)"),
		size: "large",
		fields: [{ fieldtype: "HTML", fieldname: "body" }],
	});

	const list = (rows || []).map((row) => {
		const orderBadge = `<span class="badge bg-secondary me-2">${row.lesson_order || "-"}</span>`;
		const typeBadge = row.lesson_type
			? `<span class="badge bg-light text-muted ms-2">${frappe.utils.escape_html(row.lesson_type)}</span>`
			: "";
		const publishedBadge = row.is_published
			? `<span class="indicator-pill green ms-2">${__("Published")}</span>`
			: `<span class="indicator-pill orange ms-2">${__("Draft")}</span>`;
		const link = `<a href="/desk/lesson/${encodeURIComponent(row.name)}" target="_blank">${frappe.utils.escape_html(row.title || "(Untitled)")}</a>`;
		return `<li class="list-group-item d-flex align-items-center justify-content-between">
			<div>${orderBadge}${link}${typeBadge}${publishedBadge}</div>
		</li>`;
	}).join("");

	dialog.get_field("body").$wrapper.html(`
		<div class="mb-2 text-muted small">
			${__("Sorted by")} <code>lesson_order</code> ${__("then")} <code>title</code>.
		</div>
		<ul class="list-group">
			${list || `<li class="list-group-item">${__("No lessons yet.")}</li>`}
		</ul>
	`);
	dialog.set_primary_action(__("Close"), () => dialog.hide());
	dialog.show();
}

function show_reorder_dialog(frm, initialRows) {
	let rows = [...(initialRows || [])];

	const dialog = new frappe.ui.Dialog({
		title: __("Reorder Lessons"),
		size: "large",
		primary_action_label: __("Save Order"),
		fields: [{ fieldtype: "HTML", fieldname: "body" }],
		primary_action: async () => {
			try {
				await save_lesson_order_server(frm.doc.name, rows);
				dialog.hide();
				frappe.show_alert({ message: __("Order updated"), indicator: "green" });
				frm.reload_doc();
			} catch (error) {
				console.error(error);
				const message = error && error.message ? error.message : __("An error occurred.");
				frappe.msgprint({
					title: __("Reorder failed"),
					message,
					indicator: "red",
				});
			}
		},
	});

	function renderList() {
		const items = rows.map((row, index) => `
			<li class="list-group-item d-flex align-items-center justify-content-between" data-idx="${index}">
				<div class="d-flex align-items-center">
					<span class="text-muted me-2">${(index + 1) * 10}</span>
					<strong>${frappe.utils.escape_html(row.title || "(Untitled)")}</strong>
				</div>
				<div class="btn-group btn-group-sm" role="group">
					<button type="button" class="btn btn-outline-secondary btn-up" ${index === 0 ? "disabled" : ""}>↑</button>
					<button type="button" class="btn btn-outline-secondary btn-down" ${index === rows.length - 1 ? "disabled" : ""}>↓</button>
				</div>
			</li>
		`).join("");

		dialog.get_field("body").$wrapper.html(`
			<div class="mb-2 text-muted small">
				${__("Use the arrows to move items. New")} <code>lesson_order</code> ${__("will be set to 10,20,30…")}
			</div>
			<ul class="list-group" id="reorder-lessons">
				${items || `<li class="list-group-item">${__("No lessons to reorder.")}</li>`}
			</ul>
		`);

		const list = dialog.$wrapper.find("#reorder-lessons");
		list.off("click");
		list.on("click", ".btn-up, .btn-down", function () {
			const item = $(this).closest("li");
			const index = parseInt(item.attr("data-idx"), 10);
			if ($(this).hasClass("btn-up") && index > 0) {
				[rows[index - 1], rows[index]] = [rows[index], rows[index - 1]];
			}
			if ($(this).hasClass("btn-down") && index < rows.length - 1) {
				[rows[index + 1], rows[index]] = [rows[index], rows[index + 1]];
			}
			renderList();
		});
	}

	renderList();
	dialog.show();
}

async function save_lesson_order_server(unitPlanName, rows) {
	const lesson_names = rows.map((row) => row.name);
	const response = await frappe.call({
		method: "ifitwala_ed.curriculum.doctype.lesson.lesson.reorder_lessons",
		args: { unit_plan: unitPlanName, lesson_names },
		freeze: true,
		freeze_message: __("Updating order…"),
	});
	return response && response.message;
}
