// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/setup/doctype/picture_management/picture_management.js

frappe.ui.form.on('Picture Management', {
  refresh(frm) {
    frm.add_custom_button(__('Execute Cleanup'), () => {
      frappe.confirm(
        __('⚠️ Are you sure? This will MOVE and DELETE files. Proceed?'),
        () => {
          frappe.call({
            method: 'ifitwala_ed.setup.doctype.picture_management.picture_management.run_execute',
            freeze: true,
            freeze_message: __('Executing cleanup...'),
            callback: (r) => {
              if (r.message) {
                frappe.msgprint(__('Cleanup complete!'));
                frm.reload_doc();
              }
            }
          });
        }
      );
    }); // Group name

    // Add danger style manually
    setTimeout(() => {
      $('[data-label="Execute%20Cleanup"]').removeClass('btn-primary').addClass('btn-danger');
    }, 100);
  }
});


