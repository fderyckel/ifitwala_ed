// Copyright (c) 2024, fdR and contributors
// For license information, please see license.txt

frappe.ui.form.on("Academic Year", {
  refresh: function (frm) {
    if (!frm.doc.islocal) {
      frm.add_custom_button(__("Create School Event"), function () {
        frappe.call({
          method:
            "ifitwala_ed.school_settings.doctype.academic_year.academic_year.create_calendar_event",
          doc: frm.doc,
          callback: function (r) {
            if (r.message) {
              frappe.show_alert({
                message: __("School Event created"),
                indicator: "green",
              });
              frm.reload_doc();
            } else if (r.exc) {
              frappe.msgprint(
                __("Error creating School Events " + (r.exc || "Unknown error"))
              );
            }
          },
        });
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
