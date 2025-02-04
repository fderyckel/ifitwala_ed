(() => {
  // ../ifitwala_ed/ifitwala_ed/public/js/utils.js
  frappe.provide("ifitwala_ed.utils");
  $.extend(ifitwala_ed.utils, {
    get_tree_options: function(option) {
      let unscrub_option = frappe.model.unscrub(option);
      let user_permission = frappe.defaults.get_user_permissions();
      let options;
      if (user_permission && user_permission[unscrub_option]) {
        options = user_permission[unscrub_option].map((perm) => perm.doc);
      } else {
        options = $.map(locals[`:${unscrub_option}`], function(c) {
          return c.name;
        }).sort();
      }
      return options.filter((value, index, self) => self.indexOf(value) === index);
    },
    get_tree_default: function(option) {
      let options = this.get_tree_options(option);
      if (options.includes(frappe.defaults.get_default(option))) {
        return frappe.defaults.get_default(option);
      } else {
        return options[0];
      }
    }
  });
  frappe.form.link_formatters["Employee"] = function(value, doc, df) {
    return add_link_title(value, doc, df, "employee_full_name");
  };
  function add_link_title(value, doc, df, title_field) {
    if (doc && value && doc[title_field] && doc[title_field] !== value && doc[df.fieldname] === value) {
      return value + ": " + doc[title_field];
    } else if (!value && doc.doctype && doc[title_field]) {
      return doc[title_field];
    } else {
      return value;
    }
  }

  // ../ifitwala_ed/ifitwala_ed/public/js/queries.js
  frappe.provide("ifitwala_ed.queries");
  $.extend(ifitwala_ed.queries, {
    user: function() {
      return { query: "frappe.core.doctype.user.user.user_query" };
    },
    contact_query: function(doc) {
      if (frappe.dynamic_link) {
        if (!doc[frappe.dynamic_link.fieldname]) {
          cur_frm.scroll_to_field(frappe.dynamic_link.fieldname);
          frappe.show_alert({
            message: __("Please set {0} first.", [
              __(frappe.meta.get_label(doc.doctype, frappe.dynamic_link.fieldname, doc.name))
            ]),
            indicator: "orange"
          });
        }
        return {
          query: "frappe.contacts.doctype.contact.contact.contact_query",
          filters: {
            link_doctype: frappe.dynamic_link.doctype,
            link_name: doc[frappe.dynamic_link.fieldname]
          }
        };
      }
    },
    organization_contact_query: function(doc) {
      if (!doc.organization) {
        frappe.throw(__("Please set {0}", [__(frappe.meta.get_label(doc.doctype, "organization", doc.name))]));
      }
      return {
        query: "frappe.contacts.doctype.contact.contact.contact_query",
        filters: { link_doctype: "Organization", link_name: doc.organization }
      };
    },
    address_query: function(doc) {
      if (frappe.dynamic_link) {
        if (!doc[frappe.dynamic_link.fieldname]) {
          cur_frm.scroll_to_field(frappe.dynamic_link.fieldname);
          frappe.show_alert({
            message: __("Please set {0} first.", [
              __(frappe.meta.get_label(doc.doctype, frappe.dynamic_link.fieldname, doc.name))
            ]),
            indicator: "orange"
          });
        }
        return {
          query: "frappe.contacts.doctype.address.address.address_query",
          filters: {
            link_doctype: frappe.dynamic_link.doctype,
            link_name: doc[frappe.dynamic_link.fieldname]
          }
        };
      }
    },
    organization_address_query: function(doc) {
      if (!doc.organization) {
        cur_frm.scroll_to_field("organization");
        frappe.show_alert({
          message: __("Please set {0} first.", [
            __(frappe.meta.get_label(doc.doctype, "organization", doc.name))
          ]),
          indicator: "orange"
        });
      }
      return {
        query: "frappe.contacts.doctype.address.address.address_query",
        filters: { link_doctype: "Organization", link_name: doc.organization }
      };
    },
    not_a_group_filter: function() {
      return { filters: { is_group: 0 } };
    },
    employee: function() {
      return { query: "ifitwala_ed.controllers.queries.employee_query" };
    },
    location: function(doc) {
      return {
        filters: [
          ["Location", "organization", "in", ["", cstr(doc.organization)]],
          ["Location", "is_group", "=", 0]
        ]
      };
    }
  });
  ifitwala_ed.queries.setup_queries = function(frm, options, query_fn) {
    var me = this;
    var set_query = function(doctype, parentfield) {
      var link_fields = frappe.meta.get_docfields(doctype, frm.doc.name, {
        fieldtype: "Link",
        options
      });
      $.each(link_fields, function(i, df) {
        if (parentfield) {
          frm.set_query(df.fieldname, parentfield, query_fn);
        } else {
          frm.set_query(df.fieldname, query_fn);
        }
      });
    };
    set_query(frm.doc.doctype);
    $.each(
      frappe.meta.get_docfields(frm.doc.doctype, frm.doc.name, { fieldtype: "Table" }),
      function(i, df) {
        set_query(df.options, df.fieldname);
      }
    );
  };
})();
//# sourceMappingURL=ifitwala_ed.bundle.6UQORDMW.js.map
