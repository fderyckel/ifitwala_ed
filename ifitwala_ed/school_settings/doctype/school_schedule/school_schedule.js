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

	school_calendar: async function(frm) {
		// blank out child fields when calendar changes
		frm.set_value("school", "");
		frm.clear_table("days");
		frm.refresh_fields(["school", "days"]);

		if (!frm.doc.school_calendar) return;

		// pull the calendar's root school (ancestor)
		const { message } = await frappe.db.get_value(
			"School Calendar", frm.doc.school_calendar, "school"
		);
		const root = message.school;

		frm.fields_dict.school.get_query = () => ({
			query: "ifitwala_ed.utilities.school_tree.get_school_descendants",
			filters: { root: root }
		});

		frappe.call({
			method: "ifitwala_ed.school_settings.doctype.school_schedule.school_schedule.get_first_academic_term_start",
			args: { school_calendar: frm.doc.school_calendar },
			callback: function(r) {
				if (r.message) {
					frm.set_value("first_day_of_academic_year", r.message);
				} else {
					frm.set_value("first_day_of_academic_year", "");
				}
			}
		});
	},

});
