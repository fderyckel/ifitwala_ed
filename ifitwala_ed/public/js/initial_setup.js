// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.after_ajax(() => {
  frappe.call('ifitwala_ed.setup.initial_setup.is_setup_done')
    .then(r => {
      if (r.message) return;  // already set up

      // Prompt fields
      const fields = [
        {fieldtype:'Data',         label:'Organization Name',              fieldname:'org_name',   reqd:1},
        {fieldtype:'Data',         label:'Organization Abbreviation',       fieldname:'org_abbr',   reqd:1},
        {fieldtype:'Section Break'},

        {fieldtype:'Data',         label:'Top School Name',                 fieldname:'school_name', reqd:1},
        {fieldtype:'Data',         label:'Top School Abbreviation',          fieldname:'school_abbr', reqd:1},
        {fieldtype:'Section Break'},

        // ─── new branding fields ───────────────────────────────────────────
        {fieldtype:'Attach Image', label:'Login Page Logo (app_logo)',      fieldname:'app_logo'},
        {fieldtype:'Attach Image', label:'Navbar Brand Image (brand_image)', fieldname:'brand_image'},
        // ───────────────────────────────────────────────────────────────────
      ];

      frappe.prompt(
        fields,
        (values) => {
          frappe.call({
            method: 'ifitwala_ed.setup.initial_setup.complete_initial_setup',
            args: values,
            callback: () => {
              frappe.show_alert(__('Initial setup completed!'), 5);
              setTimeout(() => location.reload(), 1200);
            }
          });
        },
        __("Ifitwala Ed – initial setup"),
        __('Create')
      );
    });
});
