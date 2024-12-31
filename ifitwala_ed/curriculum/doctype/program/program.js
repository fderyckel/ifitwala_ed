// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Program", {
  onload: function (frm) {},

  refresh: function (frm) {},

  onload_post_render: function (frm) {
    frm.get_field("courses").grid.set_multiple_add("course");
  },
});

// to filter out courses that have already been picked out in the program.
frappe.ui.form.on("Program Course", {
  courses_add: function (frm) {
    frm.fields_dict["courses"].grid.get_field("course").get_query = function (doc) {
      var course_list = [];
      if (!doc.__islocal) course_list.push(doc.name);
      $.each(doc.courses, function (idx, val) {
        if (val.course) course_list.push(val.course);
      });
      return {
        filters: [
          ["Course", "name", "not in", course_list], //Prevent to add duplicate courses on the list
          ["Course", "status", "=", "Active"], //Filter only the courses that are set to active
        ],
      };
    };
  },
});
