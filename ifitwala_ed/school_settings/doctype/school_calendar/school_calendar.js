// Copyright (c) 2024, François de Ryckel
// For license information, please see license.txt

frappe.ui.form.on("School Calendar", { 

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
    if (frappe.user_roles.includes("Schedule Maker") || frappe.user_roles.includes("Academic Admin")) {
      frm.add_custom_button(__("Clone Calendar…"), () => {
        frappe.prompt(
          [
            {
              fieldtype: "Link",
              label: "New Academic Year",
              fieldname: "academic_year",
              options: "Academic Year",
              reqd: 1
            },
            {
              fieldtype: "MultiSelect",
              label: "Target School(s)",
              fieldname: "schools",
              get_data: function (txt) {
                return new Promise((resolve) => {
                  frappe.db.get_link_options("School", txt).then(schools => {
                    resolve((schools || []).map(d => ({
                      label: d.label,
                      value: d.value
                    })));
                  });
                });
              }, 
              reqd: 1
            }
          ],
          async (values) => {
            await frappe.call({
              method: "ifitwala_ed.school_settings.doctype.school_calendar.school_calendar.clone_calendar",
              args: {
                source_calendar: frm.doc.name,
                academic_year: values.academic_year,
                schools: JSON.stringify(values.schools)
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

  school: function(frm) {

    if (frm.doc.school) {
      frappe.call({
        method: "frappe.client.get",
        args: {
          doctype: "School",
          name: frm.doc.school
        },
        callback: function (r) {
          if (r.message) {
            let schoolDoc = r.message;
            frm.set_value("break_color", schoolDoc.break_color);
            frm.set_value("weekend_color", schoolDoc.weekend_color);
          }
        }
      });
    }
  },
  
  academic_year: function (frm) {
    frm.events.get_terms(frm);
    if (frm.doc.school && frm.doc.academic_year) {
      frm.trigger("get_terms");
    }
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