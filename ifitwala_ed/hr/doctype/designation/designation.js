// Copyright (c) 2025, fdR and contributors
// For license information, please see license.txt

frappe.ui.form.on("Designation", {
    organization: function(frm) {
        set_school_filter(frm);
        set_reports_to_filter(frm);
    },

    refresh: function(frm) {
        set_organization_filter(frm);
        prefill_organization(frm);
        set_school_filter(frm);
        set_reports_to_filter(frm);
        frm.set_query("default_role_profile", () => {
            return {
                query: "ifitwala_ed.hr.doctype.designation.designation.get_assignable_roles"
            };
        });
        add_view_employees_button(frm);
    },

    archived: function(frm) {
        set_reports_to_filter(frm);
    }
});

function set_organization_filter(frm) {
    frm.set_query("organization", () => {
        return {
            filters: {
                name: ["!=", "All Organizations"]
            }
        };
    });
}

function prefill_organization(frm) {
    if (!frm.is_new() || frm.doc.organization) {
        return;
    }

    frappe.call({
        method: "ifitwala_ed.hr.doctype.designation.designation.get_default_designation_organization",
        callback: function(r) {
            const organization = r.message;
            if (organization && organization !== "All Organizations" && !frm.doc.organization) {
                frm.set_value("organization", organization);
            }
        }
    });
}

function set_school_filter(frm) {
    if (frm.doc.organization && frm.doc.organization !== "All Organizations") {
        frm.fields_dict["school"].get_query = function() {
            return {
                filters: {
                    organization: frm.doc.organization
                }
            };
        };
    } else {
        frm.set_value("school", "");
    }
}

function set_reports_to_filter(frm) {
  if (!frm.doc.organization || frm.doc.organization === "All Organizations") {
    frm.fields_dict["reports_to"].get_query = function() {
      return {
        filters: {
          name: ["!=", frm.doc.name],
          archived: 0
        }
      };
    };
    return;
  }

  // Fetch valid parent organizations
  frappe.call({
    method: "ifitwala_ed.hr.doctype.designation.designation.get_valid_parent_organizations",
    args: {
      organization: frm.doc.organization
    },
    callback: function(r) {
      if (r.message) {
        const valid_orgs = r.message;

        frm.fields_dict["reports_to"].get_query = function() {
          return {
            filters: {
              organization: ["in", valid_orgs],
              name: ["!=", frm.doc.name],
              archived: 0
            }
          };
        };
      }
    }
  });
}

function add_view_employees_button(frm) {
    if (frm.is_new() || !can_view_designation_employees()) {
        return;
    }

    frm.add_custom_button(__("View Employees"), () => open_designation_employee_dialog(frm), __("View"));
}

function can_view_designation_employees() {
    const roles = frappe.user_roles || [];
    return (
        frappe.session.user === "Administrator" ||
        roles.includes("System Manager") ||
        roles.includes("HR Manager") ||
        roles.includes("HR User")
    );
}

function open_designation_employee_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __("Employees for {0}", [frm.doc.designation_name || frm.doc.name]),
        fields: [
            {
                fieldname: "results",
                fieldtype: "HTML"
            }
        ],
        primary_action_label: __("Close"),
        primary_action() {
            dialog.hide();
        }
    });

    dialog.show();
    render_designation_employee_results(dialog, {
        designation_label: frm.doc.designation_name || frm.doc.name,
        employees: null,
        count: null
    });

    frappe.call({
        method: "ifitwala_ed.hr.doctype.designation.designation.get_scoped_designation_employees",
        args: {
            designation: frm.doc.name
        }
    }).then((r) => {
        render_designation_employee_results(dialog, r.message || {
            designation_label: frm.doc.designation_name || frm.doc.name,
            employees: [],
            count: 0
        });
    }).catch((err) => {
        dialog.hide();
        frappe.msgprint({
            title: __("Unable to Load Employees"),
            indicator: "red",
            message: err?.message || __("The employee lookup could not be completed.")
        });
    });
}

function render_designation_employee_results(dialog, payload) {
    const wrapper = dialog.get_field("results").$wrapper;
    const designationLabel = escapeHtml(payload?.designation_label || "");

    if (payload?.employees == null) {
        wrapper.html(`
            <div class="text-muted" style="padding: 12px 0;">
                ${__("Loading employees for {0}…", [designationLabel || __("this designation")])}
            </div>
        `);
        return;
    }

    const employees = Array.isArray(payload.employees) ? payload.employees : [];
    const count = Number(payload && payload.count != null ? payload.count : employees.length) || 0;

    if (!employees.length) {
        wrapper.html(`
            <div style="padding: 8px 0 4px;">
                <div style="font-weight: 600;">${designationLabel}</div>
                <div class="text-muted" style="margin-top: 6px;">
                    ${__("No employees with this designation are visible in your scope.")}
                </div>
            </div>
        `);
        return;
    }

    const rows = employees.map((employee) => {
        const employeeName = escapeHtml(employee.employee || "");
        const employeeFullName = escapeHtml(employee.employee_full_name || employee.employee || "");
        const organizations = formatScopeList(employee.organizations);
        const schools = formatScopeList(employee.schools);
        const sources = formatMatchSources(employee.match_sources);
        const historyDetails = formatHistoryDetails(employee.history_matches);

        return `
            <tr>
                <td style="vertical-align: top; min-width: 220px;">
                    <a href="#" class="designation-employee-link" data-employee="${employeeName}">${employeeFullName}</a>
                    <div class="text-muted small" style="margin-top: 4px;">${employeeName}</div>
                </td>
                <td style="vertical-align: top; min-width: 150px;">${sources || "&mdash;"}</td>
                <td style="vertical-align: top; min-width: 160px;">${organizations || "&mdash;"}</td>
                <td style="vertical-align: top; min-width: 160px;">${schools || "&mdash;"}</td>
                <td style="vertical-align: top; min-width: 240px;">${historyDetails || "&mdash;"}</td>
            </tr>
        `;
    }).join("");

    wrapper.html(`
        <div style="padding-bottom: 10px;">
            <div style="font-weight: 600;">${designationLabel}</div>
            <div class="text-muted" style="margin-top: 6px;">
                ${__("{0} employee(s) visible in your scope.", [String(count)])}
            </div>
        </div>
        <div style="max-height: 420px; overflow: auto; border: 1px solid var(--border-color); border-radius: 8px;">
            <table class="table table-bordered" style="margin-bottom: 0;">
                <thead>
                    <tr>
                        <th>${__("Employee")}</th>
                        <th>${__("Match")}</th>
                        <th>${__("Organization")}</th>
                        <th>${__("School")}</th>
                        <th>${__("Current History")}</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `);

    wrapper.find(".designation-employee-link").on("click", function(event) {
        event.preventDefault();
        const employee = $(this).data("employee");
        if (employee) {
            frappe.set_route("Form", "Employee", employee);
        }
    });
}

function formatScopeList(values) {
    if (!Array.isArray(values) || !values.length) {
        return "";
    }
    return values.map((value) => escapeHtml(value)).join("<br>");
}

function formatMatchSources(values) {
    if (!Array.isArray(values) || !values.length) {
        return "";
    }

    return values.map((value) => {
        if (value === "Primary designation") {
            return escapeHtml(__("Primary designation"));
        }
        if (value === "Current history") {
            return escapeHtml(__("Current history"));
        }
        return escapeHtml(value);
    }).join("<br>");
}

function formatHistoryDetails(historyMatches) {
    if (!Array.isArray(historyMatches) || !historyMatches.length) {
        return "";
    }

    return historyMatches.map((row) => {
        const organization = escapeHtml(row.organization || __("No organization"));
        const school = escapeHtml(row.school || __("No school"));
        const since = row.from_date ? frappe.datetime.str_to_user(row.from_date) : __("Date not set");
        return `${organization} / ${school} <span class="text-muted">(${__("since")} ${escapeHtml(since)})</span>`;
    }).join("<br>");
}

function escapeHtml(value) {
    return frappe.utils.escape_html(String(value || ""));
}
