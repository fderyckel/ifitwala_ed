// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/students/report/case_entries_activity_log/case_entries_activity_log.js

/* global frappe */

frappe.query_reports["Case Entries Activity Log"] = {
  // Render extra charts after the table is drawn (rows already in memory)
  after_datatable_render: function (report) {
    const data = report.data || [];
    if (!data.length) return;

    // Rebuild the extra charts area each refresh
    let $area = report.page.main.find(".cea-extra-charts");
    if (!$area.length) {
      $area = $(`
        <div class="cea-extra-charts" style="margin-top: 1rem;">
          <div class="row gy-4">
            <!-- Time -->
            <div class="col-12 col-lg-6">
              <div class="d-flex align-items-center justify-content-between">
                <h5 class="mb-2">${__("Entries Over Time")}</h5>
                <div>
                  <select class="form-select form-select-sm cea-bucket" style="width:auto;display:inline-block">
                    <option value="week"> ${__("Weekly")} </option>
                    <option value="month"> ${__("Monthly")} </option>
                  </select>
                </div>
              </div>
              <div class="cea-chart cea-time"></div>
            </div>

            <!-- School / Program -->
            <div class="col-12 col-lg-6">
              <div class="d-flex align-items-center justify-content-between">
                <h5 class="mb-2">${__("Entries by School / Program")}</h5>
                <div>
                  <select class="form-select form-select-sm cea-dim" style="width:auto;display:inline-block">
                    <option value="school"> ${__("School")} </option>
                    <option value="program"> ${__("Program")} </option>
                  </select>
                </div>
              </div>
              <div class="cea-chart cea-dim-chart"></div>
            </div>

            <!-- By Case Manager -->
            <div class="col-12">
              <h5 class="mb-2">${__("Entries per Case Manager")}</h5>
              <div class="cea-chart cea-manager"></div>
            </div>
          </div>
        </div>
      `).appendTo(report.page.main);
    }

    // Build datasets from table rows (no extra server calls)
    const parsed = parse_rows(data);

    // Render all charts once, then wire toggles
    render_time($area.find(".cea-time")[0], parsed, "week");
    render_dim($area.find(".cea-dim-chart")[0], parsed, "school");
    render_manager($area.find(".cea-manager")[0], parsed);

    $area.find(".cea-bucket").off("change").on("change", function () {
      render_time($area.find(".cea-time")[0], parsed, $(this).val());
    });
    $area.find(".cea-dim").off("change").on("change", function () {
      render_dim($area.find(".cea-dim-chart")[0], parsed, $(this).val());
    });
  }
};


// ---------- helpers (client-side aggregates) ----------

function parse_rows(rows) {
  const out = {
    byWeek: {},   // label -> count
    byMonth: {},  // label -> count
    bySchool: {}, // school -> count
    byProgram: {},// program -> count
    byManager: {} // case_manager_name or "(Unassigned)" -> count
  };

  rows.forEach(r => {
    const dateStr = (r.entry_date || r.entry_datetime || "").toString();
    if (dateStr) {
      const d = frappe.datetime.str_to_obj(dateStr);
      if (d) {
        const weekStart = new Date(d);
        weekStart.setDate(d.getDate() - d.getDay() + 1); // Monday
        const wlabel = frappe.format(weekStart, "Date", {format: "d MMM yyyy"});
        out.byWeek[wlabel] = (out.byWeek[wlabel] || 0) + 1;

        const mStart = new Date(d.getFullYear(), d.getMonth(), 1);
        const mlabel = frappe.format(mStart, "Date", {format: "MMM yyyy"});
        out.byMonth[mlabel] = (out.byMonth[mlabel] || 0) + 1;
      }
    }

    const school = (r.school || "").trim() || __("—");
    out.bySchool[school] = (out.bySchool[school] || 0) + 1;

    const program = (r.program || "").trim() || __("—");
    out.byProgram[program] = (out.byProgram[program] || 0) + 1;

    const mgr = (r.case_manager_name || "").trim() || __("— Unassigned —");
    out.byManager[mgr] = (out.byManager[mgr] || 0) + 1;
  });

  return out;
}

function render_time(el, parsed, bucket) {
  const src = bucket === "month" ? parsed.byMonth : parsed.byWeek;
  const labels = Object.keys(src).sort((a,b) => new Date(a) - new Date(b));
  const values = labels.map(l => src[l]);

  el.innerHTML = "";
  new frappe.Chart(el, {
    data: { labels, datasets: [{ name: __("Entries"), values }] },
    type: "line",
    height: 240
  });
}

function render_dim(el, parsed, dim) {
  const src = dim === "program" ? parsed.byProgram : parsed.bySchool;
  const labels = Object.keys(src).sort();
  const values = labels.map(l => src[l]);

  el.innerHTML = "";
  new frappe.Chart(el, {
    data: { labels, datasets: [{ name: __("Entries"), values }] },
    type: "bar",
    height: 240
  });
}

function render_manager(el, parsed) {
  // Show top N managers to keep it readable; N=12 (change as needed)
  const entries = Object.entries(parsed.byManager).sort((a,b) => b[1]-a[1]).slice(0, 12);
  const labels = entries.map(x => x[0]);
  const values = entries.map(x => x[1]);

  el.innerHTML = "";
  new frappe.Chart(el, {
    data: { labels, datasets: [{ name: __("Entries"), values }] },
    type: "bar",
    height: 260
  });
}
