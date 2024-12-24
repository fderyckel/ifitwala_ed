// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

cur_frm.add_fetch("employee", "employee_image", "image");

frappe.ui.form.on("Instructor", {
  refresh: function (frm) {},
});
