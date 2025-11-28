// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed.hr.doctype.staff_calendar.staff_calendar

frappe.ui.form.on("Staff Calendar", {
	refresh(frm) {
		// --- Totals: keep in sync with Python logic ---
		// Python: total_working_day = date_diff(to_date, from_date) + 1 - total_holidays
		if (frm.doc.holidays) {
			const holidays_count = frm.doc.holidays.length;
			frm.set_value("total_holidays", holidays_count);

			if (frm.doc.from_date && frm.doc.to_date) {
				const diff = frappe.datetime.get_day_diff(frm.doc.to_date, frm.doc.from_date) + 1;
				frm.set_value("total_working_day", diff - holidays_count);
			}
		}

		// --- Countries & subdivisions (only fetch once per form) ---
		if (!frm.subdivisions_by_country) {
			frm.call("get_supported_countries").then((r) => {
				if (!r || !r.message) return;

				frm.subdivisions_by_country = r.message.subdivisions_by_country || {};
				frm.fields_dict.country.set_data(
					(r.message.countries || []).sort((a, b) =>
						a.label.localeCompare(b.label)
					)
				);

				if (frm.doc.country) {
					frm.trigger("set_subdivisions");
				}
			});
		} else if (frm.doc.country) {
			// already have subdivisions cached, just apply
			frm.trigger("set_subdivisions");
		}

		// --- Copy from another Staff Calendar (helper for HR) ---
		if (!frm.is_new()) {
			frm.add_custom_button(
				__("Copy from another Staff Calendar"),
				() => {
					frappe.prompt(
						[
							{
								fieldname: "source_calendar",
								fieldtype: "Link",
								label: __("Source Staff Calendar"),
								options: "Staff Calendar",
								reqd: 1,
							},
						],
						(values) => {
							if (!values.source_calendar) return;

							frm
								.call("copy_from_calendar", {
									source_calendar: values.source_calendar,
								})
								.then(() => {
									frm.reload_doc();
								});
						},
						__("Select Source Calendar"),
						__("Copy")
					);
				},
				__("Actions")
			);
		}
	},

	from_date(frm) {
		// Auto-set to_date to "one year minus one day" if empty
		if (frm.doc.from_date && !frm.doc.to_date) {
			const a_year_from_start = frappe.datetime.add_months(frm.doc.from_date, 12);
			frm.set_value("to_date", frappe.datetime.add_days(a_year_from_start, -1));
		}

		// Recompute totals if we have holidays and to_date
		if (frm.doc.holidays && frm.doc.to_date) {
			const holidays_count = frm.doc.holidays.length;
			const diff = frappe.datetime.get_day_diff(frm.doc.to_date, frm.doc.from_date) + 1;
			frm.set_value("total_working_day", diff - holidays_count);
		}
	},

	country(frm) {
		frm.set_value("subdivision", "");

		if (frm.doc.country) {
			frm.trigger("set_subdivisions");
		}
	},

	set_subdivisions(frm) {
		const all = frm.subdivisions_by_country || {};
		const subdivisions = [...(all[frm.doc.country] || [])];

		if (subdivisions && subdivisions.length > 0) {
			frm.fields_dict.subdivision.set_data(subdivisions);
			frm.set_df_property("subdivision", "hidden", 0);
		} else {
			frm.fields_dict.subdivision.set_data([]);
			frm.set_df_property("subdivision", "hidden", 1);
		}
	},
});
