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
  }, 

  school_calendar: function(frm) {
    if (frm.doc.school_calendar) {
      frappe.db.get_value("School Calendar", frm.doc.school_calendar, "academic_year", function(res) {
        if (res.academic_year) {
          frappe.db.get_value("Academic Year", res.academic_year, "year_start_date", function(ay) {
            frm.set_value("first_day_of_academic_year", ay.year_start_date);
          });
        }
      });
    } else {
      frm.set_value("first_day_of_academic_year", null);
    }
  }  
});
