// Copyright (c) 2024, François de Ryckel
// For license information, please see license.txt

frappe.ui.form.on("School Calendar", { 

  // run this early so filters are set as soon as the form is loaded or refreshed
  setup: function(frm) {
    frm.set_query("academic_year", function() {
      // Only return academic years tied to the chosen school
      return {
        filters: {
          school: frm.doc.school
        }
      };
    });
  },  

  refresh: function (frm) {
    // Only proceed if school is chosen
    if (frm.doc.school) {
      frappe.call({
        method: "frappe.client.get",
        args: {
          doctype: "School",
          name: frm.doc.school
        },
        callback: function(r) {
          if (r.message) {
            // r.message holds the school doc
            let schoolDoc = r.message;
            frm.set_value("break_color", schoolDoc.break_color);
            frm.set_value("weekend_color", schoolDoc.weekend_color);
          }
        }
      });
    }
  },

  school: function(frm) {
    // Re-trigger the query whenever School changes
    frm.refresh_field("academic_year");
  },
  
  academic_year: function (frm) {
    frm.events.get_terms(frm);
  },

  get_terms: function (frm) {
    frm.set_value("terms", []);
    frappe.call({
      method: "get_terms",
      doc: frm.doc,
      callback: function (r) {
        if (r.message) {
          frm.set_value("terms", r.message);
        }
      },
    });
  },
});
