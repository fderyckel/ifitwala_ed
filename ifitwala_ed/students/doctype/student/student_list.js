// Copyright (c) 2025, François de Ryckel 
// For license information, please see license.txt

frappe.listview_settings['Student'] = {
  get_indicator: function (doc) {
      if (doc.student_gender === "Female") {
          return [__("Female"), "#FFC0CB", "gender,=,Female"]; // Light pink
      } else if (doc.student_gender === "Male") {
          return [__("Male"), "#ADD8E6", "gender,=,Male"]; // Light blue
      } else {
          return [__("Other"), "#D2B48C", "gender,=,Other"]; // Light brown (tan)
      }
  }
};