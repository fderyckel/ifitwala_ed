// Copyright (c) 2024, François de Ryckel 
// For license information, please see license.txt

frappe.ui.form.on('Student', {
  setup: function(frm) {
    frm.set_query('student', 'siblings', function(doc) {
      return {
        'filters': {'name': ['!=', doc.name]}
      };
    });
  },

  refresh: async function(frm) {
    frappe.dynamic_link = { doc: frm.doc, fieldname: 'name', doctype: 'Student' };
  
    if (!frm.is_new()) {
      frappe.contacts.render_address_and_contact(frm);
  
      // ✅ Check if linked Contact exists
      const r = await frappe.call({
        method: 'ifitwala_ed.utilities.contact_utils.get_contact_linked_to_student',
        args: { student_name: frm.doc.name }
      });
  
      // ✅ Add button only if a contact is found
      if (r.message) {
        frm.add_custom_button(__('Student Contact'), () => {
          frappe.set_route('Form', 'Contact', r.message);
        });
      }
  
    } else {
      frappe.contacts.clear_address_and_contact(frm);
    }
  }
});

