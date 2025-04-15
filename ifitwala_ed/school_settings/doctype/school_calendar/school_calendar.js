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

    frm.set_df_property("terms", "read_only", 1);
    frm.set_df_property("terms", "cannot_add_rows", true);
    frm.set_df_property("terms", "cannot_delete_rows", true);

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

    if (frm.doc.school) {
      frappe.call({
        method: "frappe.client.get",
        args: {
          doctype: "School",
          name: frm.doc.school
        },
        callback: function (r) {
          if (r.message) {
            let schoolDoc = r.message;
            frm.set_value("break_color", schoolDoc.break_color);
            frm.set_value("weekend_color", schoolDoc.weekend_color);
          }
        }
      });
    }
  },
  
  academic_year: function (frm) {
    frm.events.get_terms(frm);
    if (frm.doc.school && frm.doc.academic_year) {
      frm.trigger("get_terms");
    }
  },

  get_terms: function (frm) {
        
    // Clear existing terms before re-adding
    frm.clear_table("terms");
    frm.refresh_field("terms");
    
    frappe.call({
      method: "get_terms",
      doc: frm.doc,
      callback: function (r) {
        if (r.message) {
          // Populate fresh terms
          r.message.forEach(term => {
            let row = frm.add_child("terms", term);
          });
          frm.refresh_field("terms");
        }
      },
    });
  },
});

frappe.ui.form.on("School Calendar Holidays", {
  holiday_date: function (frm, cdt, cdn) {
    frm.save();
  }
});