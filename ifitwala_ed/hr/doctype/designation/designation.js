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
