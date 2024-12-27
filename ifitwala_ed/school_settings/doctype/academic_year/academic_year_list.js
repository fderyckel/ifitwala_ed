// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings["Academic Year"] = {
  hide_name_column: true,
  get_columns: function () {
    return [
      {
        field: "ID",
        width: "150px",
      },
      {
        field: "academic_year_name",
        width: "150px",
      },
      {
        field: "school",
        width: "200px",
      },
      {
        field: "year_start_date",
        width: "150px",
      },
    ];
  },
};
