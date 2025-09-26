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

		if (!frm.is_new() && frm.fields_dict.activities) {
			add_promote_button(frm);
		}

		frm.add_custom_button(__("Promote selected to Tasks"), async () => {
			const grid = frm.fields_dict.activities?.grid;
			const selected = grid?.get_selected_children() || [];
			if (!selected.length) {
				frappe.msgprint({ message: __("Select at least one activity row."), indicator: "orange" });
				return;
			}
			const dlg = new frappe.ui.Dialog({
				title: __("Promote selected activities"),
				fields: [
					{ fieldname: "delivery_type", fieldtype: "Select", label: __("Delivery Type (optional override)"),
						options: ["", "Assignment","Quiz","Discussion","Checkpoint","External Tool","Other"].join("\n") },
					{ fieldname: "student_group", fieldtype: "Link", label: __("Student Group"), options: "Student Group" },
					{ fieldname: "section_dates", fieldtype: "Section Break", label: __("Dates (optional)") },
					{ fieldname: "available_from", fieldtype: "Datetime", label: __("Available From") },
					{ fieldname: "due_date", fieldtype: "Datetime", label: __("Due Date") },
					{ fieldname: "available_until", fieldtype: "Datetime", label: __("Available Until") },
					{ fieldname: "col1", fieldtype: "Column Break" },
					{ fieldname: "is_published", fieldtype: "Check", label: __("Publish immediately?") },
				],
				primary_action_label: __("Create Tasks"),
				primary_action: async (v) => {
					try {
						const child_names = selected.map(r => r.name);
						const res = await frappe.call({
							method: "ifitwala_ed.curriculum.doctype.lesson.lesson.bulk_promote_activities_to_tasks",
							args: {
								lesson: frm.doc.name,
								activity_child_names: child_names,
								delivery_type: v.delivery_type || null,
								student_group: v.student_group || null,
								available_from: v.available_from || null,
								due_date: v.due_date || null,
								available_until: v.available_until || null,
								is_published: v.is_published ? 1 : 0,
							},
							freeze: true,
							freeze_message: __("Creating tasks...")
						});
						dlg.hide();
						const msg = res?.message || {};
						const created = (msg.created || []).length;
						const failed = (msg.failed || []).length;
						frappe.msgprint({
							title: __("Bulk Promote Result"),
							indicator: failed ? "orange" : "green",
							message: __(`
								<div><strong>${created}</strong> ${__("task(s) created.")}</div>
								<div><strong>${failed}</strong> ${__("failed.")}</div>
							`)
						});
						if (created === 1 && msg.created[0]) {
							frappe.set_route("Form", "Task", msg.created[0]);
						}
					} catch (e) {
						console.error(e);
						frappe.msgprint({ message: __("Failed to create tasks"), indicator: "red" });
					}
				}
			});
			dlg.show();
		}, __("Activities"));

		frm.add_custom_button(__("Duplicate selected activity"), async () => {
			const grid = frm.fields_dict.activities?.grid;
			const selected = grid?.get_selected_children() || [];
			if (!selected.length) {
				frappe.msgprint({ message: __("Select an activity row to duplicate."), indicator: "orange" });
				return;
			}
			const row = selected[0];
			try {
				await frappe.call({
					method: "ifitwala_ed.curriculum.doctype.lesson.lesson.duplicate_activity",
					args: { lesson: frm.doc.name, activity_child_name: row.name },
					freeze: true,
					freeze_message: __("Duplicating…")
				});
				frappe.show_alert({ message: __("Duplicated"), indicator: "green" });
				frm.reload_doc();
			} catch (e) {
				console.error(e);
				frappe.msgprint({ message: __("Failed to duplicate"), indicator: "red" });
			}
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
		method: "ifitwala_ed.curriculum.doctype.lesson.lesson.reorder_lesson_activities",
		args: { lesson: lesson_name, activity_names },
		freeze: true,
		freeze_message: __("Updating order…")
	});
	return res && res.message;
}


function add_promote_button(frm) {
	if (frm._promote_btn_added) return;
	frm._promote_btn_added = true;

	frm.add_custom_button(__("Promote to Task (selected activity)"), async () => {
		const grid = frm.fields_dict.activities.grid;
		const selected = grid.get_selected_children();
		if (!selected || !selected.length) {
			frappe.msgprint({ message: __("Select an activity row first."), indicator: "orange" });
			return;
		}
		const row = selected[0]; // single-row promote for v1

		// Suggest delivery_type from activity_type
		const suggested = suggest_delivery_type(row.activity_type);

		const dlg = new frappe.ui.Dialog({
			title: __("Promote Activity to Task"),
			fields: [
				{ fieldname: "delivery_type", fieldtype: "Select", label: __("Delivery Type"),
					options: ["Assignment","Quiz","Discussion","Checkpoint","External Tool","Other"].join("\n"),
					default: suggested },
				{ fieldname: "student_group", fieldtype: "Link", label: __("Student Group"), options: "Student Group" },
				{ fieldname: "section_dates", fieldtype: "Section Break", label: __("Dates (optional)") },
				{ fieldname: "available_from", fieldtype: "Datetime", label: __("Available From") },
				{ fieldname: "due_date", fieldtype: "Datetime", label: __("Due Date") },
				{ fieldname: "available_until", fieldtype: "Datetime", label: __("Available Until") },
				{ fieldname: "col1", fieldtype: "Column Break" },
				{ fieldname: "is_published", fieldtype: "Check", label: __("Publish immediately?") },
			],
			primary_action_label: __("Create Task"),
			primary_action: async (values) => {
				try {
					const res = await frappe.call({
						method: "ifitwala_ed.curriculum.doctype.lesson.lesson.promote_activity_to_task",
						args: {
							lesson: frm.doc.name,
							activity_child_name: row.name,
							delivery_type: values.delivery_type || null,
							student_group: values.student_group || null,
							available_from: values.available_from || null,
							due_date: values.due_date || null,
							available_until: values.available_until || null,
							is_published: values.is_published ? 1 : 0,
						},
						freeze: true,
						freeze_message: __("Creating task..."),
					});
					dlg.hide();
					if (res && res.message && res.message.name) {
						frappe.show_alert({ message: __("Task created: {0}", [res.message.name]), indicator: "green" });
						frappe.set_route("Form", "Task", res.message.name);
					} else {
						frappe.msgprint({ message: __("Unexpected response"), indicator: "orange" });
					}
				} catch (e) {
					console.error(e);
					frappe.msgprint({ message: __("Failed to create Task"), indicator: "red" });
				}
			}
		});
		dlg.show();
	});
}

function suggest_delivery_type(activity_type) {
	switch ((activity_type || "").trim()) {
		case "Discussion": return "Discussion";
		case "Assignment": return "Assignment";
		case "Reading":
		case "Video":
		case "Link":
			return "Checkpoint";
		default:
			return "Checkpoint";
	}
}