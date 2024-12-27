// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Education Settings", {
  onload: function (frm) {
    frm.set_query("current_term", function () {
      return {
        filters: {
          academic_year: frm.doc.current_academic_year,
        },
      };
    });
  },

  refresh: function (frm) {},
});
