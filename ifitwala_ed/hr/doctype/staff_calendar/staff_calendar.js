// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on('Staff Calendar', {

	refresh: function(frm) {
    if(frm.doc.holidays) {
      frm.set_value('total_holidays', frm.doc.holidays.length);
		}
		if(frm.doc.total_holidays) {
			var diff = frappe.datetime.get_day_diff(frappe.datetime.obj_to_str(frm.doc.to_date), frappe.datetime.obj_to_str(frm.doc.from_date));
			frm.set_value('total_working_day', (diff - frm.doc.holidays.length));
		}

    frm.call("get_supported_countries").then((r) => {
			frm.subdivisions_by_country = r.message.subdivisions_by_country;
			frm.fields_dict.country.set_data(
				r.message.countries.sort((a, b) => a.label.localeCompare(b.label))
			);

			if (frm.doc.country) {
				frm.trigger("set_subdivisions");
			}
		});
	},

  from_date: function(frm) {
    if(frm.doc.from_date && !frm.doc.to_date) {
      var a_year_from_start = frappe.datetime.add_months(frm.doc.from_date, 12);
      frm.set_value('to_date', frappe.datetime.add_days(a_year_from_start, - 1));
    }
  }, 

  country: function (frm) {
		frm.set_value("subdivision", "");

		if (frm.doc.country) {
			frm.trigger("set_subdivisions");
		}
	},
  
	set_subdivisions: function (frm) {
		const subdivisions = [...frm.subdivisions_by_country[frm.doc.country]];
		if (subdivisions && subdivisions.length > 0) {
			frm.fields_dict.subdivision.set_data(subdivisions);
			frm.set_df_property("subdivision", "hidden", 0);
		} else {
			frm.fields_dict.subdivision.set_data([]);
			frm.set_df_property("subdivision", "hidden", 1);
		}
	}, 
});