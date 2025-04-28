// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on('File Management', {
  refresh(frm) {
    frm.add_custom_button('Dry Run Cleanup', () => {
      frappe.confirm(
        'Are you sure you want to simulate the file reorganization and cleanup?',
        () => {
          frappe.call({
            method: 'ifitwala_ed.school_settings.doctype.file_management.file_management.run_dry_run',
            freeze: true,
            freeze_message: __('Simulating cleanup...'),
            callback: (r) => {
              if (r.message) {
                frappe.msgprint(__(r.message));
              }
            }
          });
        }
      );
    }, 'Actions');

    frm.add_custom_button('Execute Cleanup', () => {
      frappe.confirm(
        '⚠️ Are you absolutely sure? This will MOVE and DELETE files. Proceed?',
        () => {
          frappe.call({
            method: 'ifitwala_ed.school_settings.doctype.file_management.file_management.run_execute',
            freeze: true,
            freeze_message: __('Executing cleanup...'),
            callback: (r) => {
              if (r.message) {
                frappe.msgprint(__(r.message));
                frm.reload_doc();
              }
            }
          });
        }
      );
    }, 'Actions');
  }
});

