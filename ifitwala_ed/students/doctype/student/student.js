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


  refresh: function(frm) {
  	frappe.dynamic_link = {doc: frm.doc, fieldname: 'name', doctype: 'Student'};
  		
    if (!frm.is_new()) {
  		frappe.contacts.render_address_and_contact(frm);
  	} else {
  		frappe.contacts.clear_address_and_contact(frm);
  	}

    frappe.realtime.on('student_image_updated', (data) => {
      if (data.student === frm.doc.name) {
        frm.reload_doc().then(() => {
          frm.set_value('student_image', data.file_url);
          frappe.show_alert({message: __("Student image updated. Please save the document."), indicator: 'green'});
         });
      }
    });  
  }
});
