// Copyright (c) 2025, fdR and contributors
// For license information, please see license.txt

frappe.ui.form.on("Designation", {
  organization: function(frm) {
      if (frm.doc.organization && frm.doc.organization !== "All Organizations") {
          // Apply the dynamic filter for the selected organization
          frm.fields_dict["school"].get_query = function() {
              return {
                  filters: {
                      organization: frm.doc.organization
                  }
              };
          };
      } else {
          // Clear the school if the organization is empty or set to "All Organizations"
          frm.set_value("school", "");
      }
  },
  
  refresh: function(frm) {
      // Apply the filter on form load as well
      if (frm.doc.organization && frm.doc.organization !== "All Organizations") {
          frm.fields_dict["school"].get_query = function() {
              return {
                  filters: {
                      organization: frm.doc.organization
                  }
              };
          };
      }
  }
});
