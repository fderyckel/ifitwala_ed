// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Academic Year", {
  refresh: function (frm) {
    // Add "Retire Academic Year" button if the document is not new and is active
    if (!frm.is_new() && frm.doc.status == 1) {
      frm.add_custom_button(__("Retire Academic Year"), function() {
        frappe.confirm(
          __("This will set the status of Program enrollment to 0 (aka retired). Are you sure you want to continue?"),
          function() {
            // On confirm, call the server-side method to retire the academic year
            frappe.call({
              method: "ifitwala_ed.school_settings.doctype.academic_year.academic_year.retire_academic_year", 
              args: {
                academic_year: frm.doc.name
              },
              callback: function(r) {
                if (r.message) {
                  frappe.msgprint(r.message);
                  // Optionally update the form field to reflect the retired status
                  // Reload the doc from the server so status and timestamp are synced
                  frm.reload_doc();
                }
              }
            });
          },
          function() {
            // On cancel, do nothing
          }
        );
      }).addClass("btn btn-danger");
    }
    
    // Custom button for creating term
    if (!frm.is_new()) {
      frm.add_custom_button(__("Create Term"), () => {
        frappe.new_doc("Term", {}, ay => {
          ay.academic_year = frm.doc.name;
        });
      });

      frm.add_custom_button(__("Create School Calendar"), () => {
        frappe.new_doc("School Calendar", {}, ay => {
          ay.academic_year = frm.doc.name; 
        })
      }); 
    }
  },

  year_start_date: function (frm) {
    if (frm.doc.year_start_date && !frm.doc.year_end_date) {
      var a_year_from_start = frappe.datetime.add_months(
        frm.doc.year_start_date,
        12
      );
      frm.set_value(
        "year_end_date",
        frappe.datetime.add_days(a_year_from_start, -1)
      );
    }
  },
});
