// Copyright (c) 2025, fdR and contributors
// For license information, please see license.txt

frappe.ui.form.on("Designation", {
    organization: function(frm) {
        set_school_filter(frm);
        set_reports_to_filter(frm);
    },

    refresh: function(frm) {
        set_school_filter(frm);
        set_reports_to_filter(frm);
    },

    archived: function(frm) {
        set_reports_to_filter(frm);
    }
});

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