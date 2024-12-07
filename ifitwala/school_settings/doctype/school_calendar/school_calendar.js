// Copyright (c) 2024, François de Ryckel
// For license information, please see license.txt

frappe.ui.form.on("School Calendar", {
  onload: function (frm) {
    if (frm.doc.school) {
      frm.set_query("academic_year", function () {
        return {
          filters: {
            school: frm.doc.school,
          },
        };
      });
    }
  },

  refresh: function (frm) {
    if (frm.doc.__onload) {
      frm.set_value("weekend_color", frm.doc.__onload.weekend_color);
      frm.set_value("break_color", frm.doc.__onload.break_color);
    }
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
