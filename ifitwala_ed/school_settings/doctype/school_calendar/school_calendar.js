// Copyright (c) 2024, François de Ryckel
// For license information, please see license.txt

frappe.ui.form.on("School Calendar", { 

	setup(frm) {
		frm.set_query("academic_year", function () {
			return {
				query: "ifitwala_ed.utilities.link_queries.academic_year_link_query",
				// when a school is already chosen, scope AYs; server falls back to user's default school if not provided
				filters: { school: frm.doc.school || undefined },
			};
		});
	},

	onload: function(frm) {
		// Use the grid's refresh event
    frm.fields_dict.terms.grid.on("refresh", function(grid) {
      grid.grid_rows.forEach(function(row) {
        // 'number_of_instructional_days' field in the child table
        let field = row.grid_form && row.grid_form.fields_dict["number_of_instructional_days"];
        if (field && field.wrapper) {
          // Use jQuery for cross-version compatibility, or plain JS if you prefer
          $(field.wrapper).css({
            "background-color": "#FFF4E5",
            "color": "#333",
            "font-weight": "bold"
          });
        }
      });
    });
	},	

	refresh: function (frm) {

		frm.set_df_property("terms", "read_only", 1);
		frm.set_df_property("terms", "cannot_add_rows", true);
		frm.set_df_property("terms", "cannot_delete_rows", true);

		// Only proceed if school is chosen
		if (frm.doc.school) {
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "School",
					name: frm.doc.school
				},
				callback: function(r) {
					if (r.message) {
						// r.message holds the school doc
						let schoolDoc = r.message;
						frm.set_value("break_color", schoolDoc.break_color);
						frm.set_value("weekend_color", schoolDoc.weekend_color);
					}
				}
			});
		}

		// button to school schedule
		if (frm.doc.school && frm.doc.academic_year) {
			frm.add_custom_button(__("Go to School Schedule"), function () {
				const route_options = {
					school: frm.doc.school,
					school_calendar: frm.doc.name,
				};
				frappe.set_route("Form", "School Schedule", route_options);
			}); 
		}
		
		// Clone Calendar button
		if (frappe.user_roles.includes("Schedule Maker") || 
				frappe.user_roles.includes("Academic Admin") || 
				frappe.user_roles.includes("Academic Assistant")) {
			frm.add_custom_button(__("Clone Calendar…"), () => {
				frappe.prompt(
					[
						{
							fieldtype: "Link",
							label: "New Academic Year",
							fieldname: "academic_year",
							options: "Academic Year",
							reqd: 1, 
							get_query: () => ({
								query: "ifitwala_ed.utilities.link_queries.academic_year_link_query",
								filters: { school: frm.doc.school || undefined },
							}),
						},
						{
							fieldtype: "Link",
							label: "Target School",
							fieldname: "school",
							options: "School",
							reqd: 1
						}
					],
					async (values) => {
						await frappe.call({
							method: "ifitwala_ed.school_settings.doctype.school_calendar.school_calendar.clone_calendar",
							args: {
								source_calendar: frm.doc.name,
								academic_year: values.academic_year,
								schools: JSON.stringify([values.school])  // wrap in array
							},
							callback: r => {
								frappe.msgprint(r.message);
							}
						});
					},
					__("Clone Calendar"),
					__("Create")
				);
			});
		}
	},   
	
	after_save: function(frm) {
        frm.fields_dict["terms"].grid.refresh();
  }, 
	
	academic_year: async function(frm) {
		// reset on change
		frm.set_value("school", "");
		frm.clear_table("terms");
		frm.refresh_fields(["school", "terms"]);

		if (!frm.doc.academic_year) {
			return;
		}

		// 1 ▸ find the AY’s own school (root of allowed tree)
		const { message } = await frappe.db.get_value(
			"Academic Year",
			frm.doc.academic_year,
			"school"
		);
		const root = message.school;

		// 2 ▸ constrain the School dropdown *before* user opens it
		frm.fields_dict.school.get_query = function() {
			return {
				query: "ifitwala_ed.utilities.school_tree.get_school_descendants",
				filters: { root: root }        // passed to the python helper
			};
		};
	},

	// ------------------------------------------------------------------
	school: function(frm) {
		// User picked a school: pull break/weekend colors
		if (!frm.doc.school) return;

		frappe.db.get_doc("School", frm.doc.school)
			.then(doc => {
				frm.set_value("break_color", doc.break_color);
				frm.set_value("weekend_color", doc.weekend_color);
			});
	},

	get_terms: function (frm) {
			
		// Clear existing terms before re-adding
		frm.clear_table("terms");
		frm.refresh_field("terms");
		
		frappe.call({
			method: "get_terms",
			doc: frm.doc,
			callback: function (r) {
				if (r.message) {
					// Populate fresh terms
					r.message.forEach(term => {
						let row = frm.add_child("terms", term);
					});
					frm.refresh_field("terms");
				}
			},
		});
	},
});

frappe.ui.form.on("School Calendar Holidays", {
	holiday_date: function (frm, cdt, cdn) {
		frm.save();
	}
});

