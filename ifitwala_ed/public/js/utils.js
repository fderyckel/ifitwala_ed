// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt


frappe.provide("ifitwala_ed.utils");

$.extend(ifitwala_ed.utils, { 
  
  get_tree_options: function (option) {
    // get valid options for tree based on user permission & locals dict
    let unscrub_option = frappe.model.unscrub(option);
    let user_permission = frappe.defaults.get_user_permissions();
    let options;

    if (user_permission && user_permission[unscrub_option]) {
      options = user_permission[unscrub_option].map((perm) => perm.doc);
    } else {
      options = $.map(locals[`:${unscrub_option}`], function (c) {
        return c.name;
      }).sort();
    }

    // filter unique values, as there may be multiple user permissions for any value
    return options.filter((value, index, self) => self.indexOf(value) === index);
  },

  get_tree_default: function (option) {
    // set default for a field based on user permission
    let options = this.get_tree_options(option);
    if (options.includes(frappe.defaults.get_default(option))) {
      return frappe.defaults.get_default(option);
    } else {
      return options[0];
    }
  },
});

frappe.form.link_formatters["Employee"] = function (value, doc, df) {
	return add_link_title(value, doc, df, "employee_full_name");
};

/**
 * Add a title to a link value based on the provided document and field information.
 *
 * @param {string} value - The value to add a link title to.
 * @param {Object} doc - The document object.
 * @param {Object} df - The field object.
 * @param {string} title_field - The field name for the title.
 * @returns {string} - The link value with the added title.
 */
function add_link_title(value, doc, df, title_field) {
	if (doc && value && doc[title_field] && doc[title_field] !== value && doc[df.fieldname] === value) {
		return value + ": " + doc[title_field];
	} else if (!value && doc.doctype && doc[title_field]) {
		return doc[title_field];
	} else {
		return value;
	}
}
