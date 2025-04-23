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

    if (column.fieldname === "type") {
      if (data.type === "Missing Program") {
        value = `<span style="color: red; font-weight: bold;">${value}</span>`;
      } else if (data.type === "Missing Student Group") {
        value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
      }
    }

    // 📐 Center-align certain fields
    const centerAligned = ["term", "program", "missing"];
    if (centerAligned.includes(column.fieldname)) {
      value = `<div style="text-align: center;">${value}</div>`;
    }

    return value;
  }    

};
