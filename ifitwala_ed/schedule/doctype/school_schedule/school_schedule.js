// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on('School Schedule', {
  refresh: function(frm) {
      // Add Clear Schedule button functionality
      frm.add_custom_button(__('Clear Schedule'), function() {
          frappe.call({
              method: "ifitwala_ed.ifitwala_ed.doctype.school_schedule.school_schedule.clear_schedule",
              doc: frm.doc,
              callback: function(response) {
                  if (!response.exc) {
                      frappe.msgprint(__('Schedule Cleared Successfully.'));
                      frm.reload_doc();
                  }
              }
          });
      }).addClass("btn-danger");

      // Add Generate Blocks button functionality
      frm.add_custom_button(__('Generate Blocks'), function() {
          frappe.call({
              method: "ifitwala_ed.ifitwala_ed.doctype.school_schedule.school_schedule.generate_blocks",
              doc: frm.doc,
              callback: function(response) {
                  if (!response.exc) {
                      frappe.msgprint(__('Blocks Generated Successfully.'));
                      frm.reload_doc();
                  }
              }
          });
      }).addClass("btn-primary");
  },

  school: function(frm) {
      // Filter School Calendar based on the selected School
      if (frm.doc.school) {
          frm.set_query("calendar", function() {
              return {
                  filters: {
                      school: frm.doc.school
                  }
              };
          });
      } else {
          // Reset filter when no school is selected
          frm.set_query("calendar", function() {
              return {};
          });
      }
  }
});
