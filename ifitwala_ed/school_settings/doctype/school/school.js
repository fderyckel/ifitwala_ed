// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

frappe.provide("ifitwala_ed.school");

frappe.ui.form.on("School", {
  onload: function (frm) {
    if (frm.doc.__islocal && frm.doc.parent_school) {
      frappe.db.get_value("School", frm.doc.parent_school, "is_group", (r) => {
        if (!r.is_group) {
          frm.set_value("parent_school", "");
        }
      });
    }
  },

  setup: function (frm) {
    frm.set_query("parent_school", function () {
      return {
        filters: { is_group: 1 },
      };
    });
  },

  refresh: function (frm) { 
    if(!frm.is_new()) {
      frm.add_custom_button(__("Create Academic Year"), () => {
        frappe.new_doc("Academic Year", {}, ay => {
          ay.school = frm.doc.name;
        });
      });

      frm.add_custom_button(__("Create School Calendar"), () => {
        frappe.new_doc("School Calendar", {}, sc => {
          sc.school = frm.doc.name;
        });
      });

      frm.add_custom_button(__('Add to Website'), () => {
        frappe.call({
          method: 'ifitwala_ed.school.doctype.school.school.add_school_to_navbar',
          args: {
              school_name: frm.doc.school_name,
              abbreviation: frm.doc.abbreviation,
              website_slug: frm.doc.website_slug || null
          },
          callback: (r) => {
              if (r.message) {
                  frappe.msgprint(r.message);
              }
          }
      });
    });
    }

    if (!frm.doc.__islocal) {
      frm.doc.abbr && frm.set_df_property("abbr", "read_only", 1);
      frm.set_df_property("parent_school", "read_only", 1);
    }

    frm.toggle_display("address_html", !frm.doc.__islocal);
    if (!frm.doc.__islocal) {
      frappe.contacts.render_address_and_contact(frm);
    }

    frm.set_query("current_school_calendar", function() {
      return { 
        filters: {school: frm.doc.name}
      }
    });
  }, 

  school_name: function (frm) {
    if (frm.doc.__islocal) {
      let parts = frm.doc.school_name.split();
      let abbr = $.map(parts, function (p) {
        return p ? p.substr(0, 1) : null;
      }).join("");
      frm.set_value("abbr", abbr);
    }
  },

  parent_school: function (frm) {
    var bool = frm.doc.parent_school ? true : false;
    frm.set_value("existing_school", bool ? frm.doc.parent_school : "");
  },

});

cur_frm.cscript.change_abbr = function () {
  var dialog = new frappe.ui.Dialog({
    title: "Replace Abbr",
    fields: [
      {
        fieldtype: "Data",
        label: "New Abbreviation",
        fieldname: "new_abbr",
        reqd: 1,
      },
      { fieldtype: "Button", label: "Update", fieldname: "update" },
    ],
  });

  dialog.fields_dict.update.$input.click(function () {
    var args = dialog.get_values();
    if (!args) return;
    frappe.show_alert(__("Update in progress. It might take a while."));
    return frappe.call({
      method:
        "ifitwala_ed.school_settings.doctype.school.school.enqueue_replace_abbr",
      args: {
        school: cur_frm.doc.name,
        old: cur_frm.doc.abbr,
        new: args.new_abbr,
      },
      callback: function (r) {
        if (r.exc) {
          frappe.msgprint(__("There were errors."));
          return;
        } else {
          cur_frm.set_value("abbr", args.new_abbr);
        }
        dialog.hide();
        cur_frm.refresh();
      },
      btn: this,
    });
  });
  dialog.show();
};

ifitwala_ed.school.set_custom_query = function (frm, v) {
  var filters = {
    school: frm.doc.name,
    is_group: 0,
  };

  for (var key in v[1]) {
    filters[key] = v[1][key];
  }

  frm.set_query(v[0], function () {
    return {
      filters: filters,
    };
  });
};
