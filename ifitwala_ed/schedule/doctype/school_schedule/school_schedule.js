// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on('School Schedule', {

  school: function(frm) {
      // Filter School Calendar based on the selected School
      if (frm.doc.school) {
          frm.set_query("school_calendar", function() {
              return {
                  filters: {
                      school: frm.doc.school
                  }
              };
          });
      } else {
          // Reset filter when no school is selected
          frm.set_query("school_calendar", function() {
              return {};
          });
      }
  }
});
