frappe.query_reports["Enrollment Gaps Report"] = {
  filters: [
    {
      fieldname: "academic_year",
      label: __("Academic Year"),
      fieldtype: "Link",
      options: "Academic Year",
      reqd: 1
    }
  ], 

  formatter: function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);

    // Pale color styling for type column
    if (column.fieldname === "type") {
      if (data.type === "Missing Program") {
        value = `<span style="color: rgba(255, 99, 71, 0.6); font-weight: bold;">${value}</span>`;
      } else if (data.type === "Missing Student Group") {
        value = `<span style="color: rgba(255, 165, 0, 0.6); font-weight: bold;">${value}</span>`;
      }
    }

    // 📐 Center-align certain fields
    const centerAligned = ["term", "program", "missing"];
    if (centerAligned.includes(column.fieldname)) {
      value = `<div style="text-align: center;">${value}</div>`;
    }
    // 📐 Left-align certain fields
    const leftAligned = ["type", "student", "student_name", "course"];
    if (leftAligned.includes(column.fieldname)) {
      value = `<div style="text-align: left;">${value}</div>`;
    }

    return value;
  }    

};
