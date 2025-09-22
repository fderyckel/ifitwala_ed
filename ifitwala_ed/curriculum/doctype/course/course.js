// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Course", {
  setup: function (frm) {
    frm.add_fetch("team", "school", "school");
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


// to filter out assessment criteria that have already been picked out in the course.
// BUGS: #2 this filter is still not working properly.  It is not filtering out the already selected assessment criteria.
frappe.ui.form.on("Course Assessment Criteria", {
  assessment_criteria_add: function (frm) {
    frm.fields_dict["assessment_criteria"].grid.get_field("assessment_criteria").get_query = function (doc) {
      var criteria_list = [];
      if (!doc.__islocal) criteria_list.push(doc.name);
      $.each(doc.assessment_criteria, function (idx, val) {
        if (val.assessment_criteria)
          criteria_list.push(val.assessment_criteria);
      });
      return {
        filters: [
          ["Assessment Criteria", "course_group", "=", frm.doc.course_group], 
          ["Assessment Criteria", "name", "not in", criteria_list]
        ],
      };
    };
  },
});

let get_programs_without_course = function (course) {
  return frappe.call({
    type: "GET",
    method:
      "ifitwala_ed.curriculum.doctype.course.course.get_programs_without_course",
    args: { course: course },
  });
};



async function fetch_units(course_name) {
	// Lean server fetch; sort by unit_order then name. Falls back gracefully if unit_order is null.
	const rows = await frappe.db.get_list("Learning Unit", {
		fields: ["name", "unit_name", "unit_order", "unit_status"],
		filters: { course: course_name },
		order_by: "unit_order asc, unit_name asc",
		limit: 500
	});
	// Normalize nulls so UI behaves consistently
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
	// Work on a copy so we can mutate safely
	let rows = [...(initialRows || [])];

	const d = new frappe.ui.Dialog({
		title: __("Reorder Units"),
		size: "large",
		primary_action_label: __("Save Order"),
		primary_action: async () => {
			await save_unit_order(rows);
			d.hide();
			frappe.show_alert({ message: __("Order updated"), indicator: "green" });
			frm.reload_doc();
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

		// Wire buttons
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

async function save_unit_order(rows) {
	// Assign new spaced order values (10,20,30…)
	const updates = rows.map((r, i) => ({
		name: r.name,
		unit_order: (i + 1) * 10
	}));

	// For small lists this is fine. If you need to optimize later,
	// we can replace this with a single whitelisted bulk-update.
	for (const u of updates) {
		// eslint-disable-next-line no-await-in-loop
		await frappe.db.set_value("Learning Unit", u.name, "unit_order", u.unit_order);
	}
}

