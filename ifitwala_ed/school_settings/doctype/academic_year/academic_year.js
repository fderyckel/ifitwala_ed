// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/school_settings/doctype/academic_year/academic_year.js

frappe.ui.form.on("Academic Year", {
  refresh: function (frm) {
    if (!frm.is_new()) {
      frm.add_custom_button(__("Open End of Year Checklist"), function() {
        frappe.route_options = {
          from_academic_year_form: 1,
          school: frm.doc.school || "",
          academic_year: frm.doc.name || "",
        };
        frappe.set_route("Form", "End of Year Checklist");
      });
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
