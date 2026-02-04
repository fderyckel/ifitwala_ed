// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/curriculum/doctype/course/course.js

frappe.ui.form.on("Course", {
	setup(frm) {
		frm.add_fetch("team", "school", "school");

		const table = frm.fields_dict.assessment_criteria;
		if (!table || !table.grid) {
			// Field renamed/removed – fail quietly
			return;
		}

		table.grid
			.get_field("assessment_criteria")
			.get_query = function (doc, cdt, cdn) {
				const selected = (doc.assessment_criteria || [])
					.map(row => row.assessment_criteria)
					.filter(v => !!v);

				const filters = [];

				// Only filter by course_group if set; otherwise don't block everything.
				if (frm.doc.course_group) {
					filters.push(["Assessment Criteria", "course_group", "=", frm.doc.course_group]);
				}

				if (selected.length) {
					filters.push(["Assessment Criteria", "name", "not in", selected]);
				}

				return { filters };
			};
	},


  onload: function (frm) {},

  refresh: function (frm) {
		if (frm.is_new() || !frm.doc.name) return;
    if (!cur_frm.doc.__islocal) {
      frm.add_custom_button(
        __("Add to Programs"),
        function () {
          frm.trigger("add_course_to_programs");
        }
      );
    }

		frm.add_custom_button(__("View Units (ordered)"), async () => {
			const rows = await fetch_units(frm.doc.name);
			show_units_dialog(rows);
		}, __("Units"));

		frm.add_custom_button(__("Reorder Units"), async () => {
			const rows = await fetch_units(frm.doc.name);
			show_reorder_dialog(frm, rows);
		}, __("Units"));

    // to only suggest grade scale that are submitted (not cancel nor draft)
    frm.set_query("default_grade_scale", function () {
      return {
        filters: {
          docstatus: 1,
        },
      };
    });
  },


  add_course_to_programs: function (frm) {
    get_programs_without_course(frm.doc.name).then((r) => {
      if (r.message.length) {
        frappe.prompt(
          [
            {
              fieldname: "programs",
              label: __("Programs"),
              fieldtype: "MultiSelectPills",
              get_data: function () {
                return r.message;
              },
            },
            {
              fieldtype: "Check",
              label: __("Is Mandatory"),
              fieldname: "mandatory",
            },
          ],
          function (data) {
            frappe.call({
              method:
                "ifitwala_ed.curriculum.doctype.course.course.add_course_to_programs",
              args: {
                course: frm.doc.name,
                programs: data.programs,
                mandatory: data.mandatory,
              },
              callback: function (r) {
                if (!r.exc) {
                  frm.reload_doc();
                }
              },
              freeze: true,
              freeze_message: __("...Adding Course to Programs"),
            });
          },
          __("Add Course to Programs"),
          __("Add")
        );
      } else {
        frappe.msgprint(
          __("This course is already added to the existing programs")
        );
      }
    });
  },
});




// ---- server calls ----

let get_programs_without_course = function (course) {
  return frappe.call({
    type: "GET",
    method:
      "ifitwala_ed.curriculum.doctype.course.course.get_programs_without_course",
    args: { course: course },
  });
};

// ---- helpers ----

async function fetch_units(course_name) {
	// Lean client fetch: order by unit_order then unit_name.
	const rows = await frappe.db.get_list("Learning Unit", {
		fields: ["name", "unit_name", "unit_order", "unit_status"],
		filters: { course: course_name },
		order_by: "unit_order asc, unit_name asc",
		limit: 1000
	});
	return (rows || []).map(r => ({
		name: r.name,
		unit_name: r.unit_name || "(Untitled)",
		unit_order: Number.isFinite(+r.unit_order) ? +r.unit_order : 0,
		unit_status: r.unit_status || ""
	}));
}

function show_units_dialog(rows) {
	const d = new frappe.ui.Dialog({
		title: __("Units (ordered)"),
		size: "large"
	});

	const list = (rows || []).map(r => {
		const orderBadge = `<span class="badge bg-secondary me-2">${r.unit_order || "-"}</span>`;
		const statusBadge = r.unit_status
			? `<span class="badge bg-light text-muted ms-2">${frappe.utils.escape_html(r.unit_status)}</span>`
			: "";
		const link = `<a href="/app/learning-unit/${encodeURIComponent(r.name)}" target="_blank">${frappe.utils.escape_html(r.unit_name)}</a>`;
		return `<li class="list-group-item d-flex align-items-center justify-content-between">
			<div>${orderBadge}${link}${statusBadge}</div>
		</li>`;
	}).join("");

	d.set_message(`
		<div class="mb-2 text-muted small">
			${__("Sorted by")} <code>unit_order</code> ${__("then")} <code>unit_name</code>.
		</div>
		<ul class="list-group">${list || `<li class="list-group-item">${__("No units yet.")}</li>`}</ul>
	`);

	d.set_primary_action(__("Close"), () => d.hide());
	d.show();
}

function show_reorder_dialog(frm, initialRows) {
	let rows = [...(initialRows || [])];

	const d = new frappe.ui.Dialog({
		title: __("Reorder Units"),
		size: "large",
		primary_action_label: __("Save Order"),
		primary_action: async () => {
			try {
				await save_unit_order_server(frm.doc.name, rows);
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
					<strong>${frappe.utils.escape_html(r.unit_name)}</strong>
				</div>
				<div class="btn-group btn-group-sm" role="group">
					<button type="button" class="btn btn-outline-secondary btn-up" ${idx === 0 ? "disabled" : ""}>↑</button>
					<button type="button" class="btn btn-outline-secondary btn-down" ${idx === rows.length - 1 ? "disabled" : ""}>↓</button>
				</div>
			</li>`;
		}).join("");

		d.set_message(`
			<div class="mb-2 text-muted small">
				${__("Use the arrows to move items. New")} <code>unit_order</code> ${__("will be set to 10,20,30…")}
			</div>
			<ul class="list-group" id="reorder-list">
				${items || `<li class="list-group-item">${__("No units to reorder.")}</li>`}
			</ul>
		`);

		const $list = d.$wrapper.find("#reorder-list");
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

async function save_unit_order_server(course_name, rows) {
	const unit_names = rows.map(r => r.name);
	const res = await frappe.call({
		method: "ifitwala_ed.curriculum.doctype.learning_unit.learning_unit.reorder_learning_units",
		args: { course: course_name, unit_names },
		freeze: true,
		freeze_message: __("Updating order…")
	});
	return res && res.message;
}
