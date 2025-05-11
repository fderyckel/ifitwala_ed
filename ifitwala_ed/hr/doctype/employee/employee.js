// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.provide("ifitwala_ed.hr");

frappe.ui.form.on("Employee", {
  setup: function (frm) {
    frm.fields_dict.user_id.get_query = function (doc) {
      return {
        query: "frappe.core.doctype.user.user.user_query",
        filters: { ignore_user_type: 1 },
      };
    };
    frm.fields_dict.reports_to.get_query = function (doc) {
      return { query: "ifitwala_ed.controllers.queries.employee_query" };
    };
  },

  onload: function (frm) {
    if (frm.doc.organization) {
      frm.set_query("school", function () {
        return {
          filters: { organization: frm.doc.organization },
        };
      });
    }
  },

  refresh: function (frm) {
    frappe.dynamic_link = {
      doc: frm.doc,
      fieldname: "name",
      doctype: "Employee",
    };

    if (!frm.is_new()) {
      frappe.contacts.render_address_and_contact(frm);
    } else {
      frappe.contacts.clear_address_and_contact(frm);
    }

    (frm.doc.employee_history || []).forEach(row => {
			const grid_row = frm.get_field('employee_history').grid.grid_rows_by_docname[row.name];
			if (row.designation) {
				grid_row.wrapper.css({
					"background-color": "#e0ffe0", // Light green for current roles
					"border-left": "4px solid #00c853" // Bold green border for emphasis
				});
			}
		});
  },

  create_user: function (frm) {
    if (!frm.doc.employee_professional_email) {
      frappe.throw(__("Please enter Professional Email"));
    }
    frappe.call({
      method: "ifitwala_ed.hr.doctype.employee.employee.create_user",
      args: { employee: frm.doc.name, email: frm.doc.employee_professional_email },
      callback: function (r) {
        frm.set_value("user_id", r.message);
      },
    });
  },

  school: function (frm) {
    if (frm.doc.school) {
      frappe.call({
        method: "frappe.client.get",
        args: {
          doctype: "School",
          name: frm.doc.school,
        },
        callback: function (data) {
          let values = {
            organization: data.message.organization,
          };
          frm.set_value(values);
        },
      });
    }
  },

  employee_salutation: function (frm) {
    if (frm.doc.employee_salutation) {
      frm.set_value(
        "employee_gender",
        {
          Mr: "Male",
          Mrs: "Female",
          Ms: "Female",
          Miss: "Female",
          Master: "Male",
          Madam: "Female",
        }[frm.doc.employee_salutation]
      );
    }
  },
});
