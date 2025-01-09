// Copyright (c) 2025, François de Ryckel 
// For license information, please see license.txt

frappe.listview_settings['Student'] = {
  get_indicator: function (doc) {
      if (doc.student_gender === "Female") {
          return [__("Female"), "female-indicator", "student_gender,=,Female"]; // Light pink
      } else if (doc.student_gender === "Male") {
          return [__("Male"), "male-indicator", "student_gender,=,Male"]; // Light blue
      } else {
          return [__("Other"), "other-indicator", "student_gender,=,Other"]; // Light brown (tan)
      }
  }
};