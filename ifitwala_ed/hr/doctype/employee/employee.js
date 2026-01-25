// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/hr/doctype/employee/employee.js
//
// NOTE:
// - Address is rendered here for HR convenience only (saves a click).
// - Contact (and Address linked to Contact) is the single source of truth.
// - Employee must not create/edit contact/address data from this form.
// - Use the "Contact" button to manage details in the Contact doctype.

frappe.provide("ifitwala_ed.hr");

frappe.ui.form.on("Employee", {
  setup(frm) {
    frm.fields_dict.user_id.get_query = function () {
      return {
        query: "frappe.core.doctype.user.user.user_query",
        filters: { ignore_user_type: 1 },
      };
    };

    frm.fields_dict.reports_to.get_query = function () {
      return { query: "ifitwala_ed.controllers.queries.employee_query" };
    };
  },

  onload(frm) {
    frm.trigger("set_school_query");
  },

  refresh(frm) {
    frappe.dynamic_link = {
      doc: frm.doc,
      fieldname: "name",
      doctype: "Employee",
    };

    frm.trigger("render_contact_address_readonly");
    frm.trigger("add_contact_button");
    frm.trigger("style_employee_history_rows");
    frm.trigger("setup_governed_image_upload");
  },

  // ------------------------------------------------------------
  // UI Helpers
  // ------------------------------------------------------------

  set_school_query(frm) {
    frm.set_query("school", () => {
      // If organization not set, do not hard-filter (avoid locking user out)
      if (!frm.doc.organization) return {};
      return { filters: { organization: frm.doc.organization } };
    });
  },

  render_contact_address_readonly(frm) {
    // Keep the convenience rendering, but treat it as DISPLAY ONLY.
    // We keep the standard renderer and then hard-disable the "create/edit" actions.

    if (frm.is_new()) {
      frappe.contacts.clear_address_and_contact(frm);
      return;
    }

    frappe.contacts.render_address_and_contact(frm);

    // Defer DOM tweaks to after the renderer paints.
    // We intentionally do this on every refresh because the section re-renders.
    setTimeout(() => {
      ifitwala_ed.hr._lock_contact_address_ui(frm);
    }, 0);
  },

  add_contact_button(frm) {
    if (!frm.is_new() && frm.doc.empl_primary_contact) {
      frm.add_custom_button(
        __("Contact"),
        () => frappe.set_route("Form", "Contact", frm.doc.empl_primary_contact),
        __("View")
      );
    }
  },

  style_employee_history_rows(frm) {
    (frm.doc.employee_history || []).forEach((row) => {
      if (!row.is_current) return;

      const grid = frm.get_field("employee_history")?.grid;
      const grid_row = grid?.grid_rows_by_docname?.[row.name];
      if (!grid_row) return;

      grid_row.wrapper.css({
        "background-color": "#e0ffe0", // Light green for current roles
        "border-left": "4px solid #00c853", // Bold green border for emphasis
      });
    });
  },

  setup_governed_image_upload(frm) {
    const fieldname = "employee_image";
    const openUploader = () => {
      if (frm.is_new()) {
        frappe.msgprint(__("Please save the Employee before uploading an image."));
        return;
      }

      new frappe.ui.FileUploader({
        method: "ifitwala_ed.utilities.governed_uploads.upload_employee_image",
        args: { employee: frm.doc.name },
        doctype: "Employee",
        docname: frm.doc.name,
        fieldname,
        allow_multiple: false,
        on_success(file_doc) {
          const payload = file_doc?.message
            || (Array.isArray(file_doc) ? file_doc[0] : file_doc)
            || (typeof file_doc === "string" ? { file_url: file_doc } : null);
          if (!payload || !payload.file_url) {
            frappe.msgprint(__("Upload succeeded but no file URL was returned."));
            return;
          }
          frm.set_value(fieldname, payload.file_url);
          frm.refresh_field(fieldname);
          frm.reload_doc();
        },
      });
    };

    frm.set_df_property(fieldname, "read_only", 1);
    frm.set_df_property(
      fieldname,
      "description",
      __("Use the Upload Employee Image action to attach a governed file.")
    );

    frm.remove_custom_button(__("Upload Employee Image"), __("Actions"));
    frm.remove_custom_button(__("Upload Employee Image"));
    const $actionBtn = frm.add_custom_button(
      __("Upload Employee Image"),
      openUploader
    );
    $actionBtn.addClass("btn-primary");

    const wrapper = frm.get_field(fieldname)?.$wrapper;
    if (wrapper?.length && !wrapper.find(".governed-upload-btn").length) {
      const $container = wrapper.find(".control-input").length
        ? wrapper.find(".control-input")
        : wrapper;
      const $btn = $(
        `<button type="button" class="btn btn-xs btn-primary governed-upload-btn">
          ${__("Upload Employee Image")}
        </button>`
      );
      $btn.on("click", openUploader);
      $container.append($btn);
    }

    if (frm.is_new()) {
      return;
    }

    frm.call({
      method: "ifitwala_ed.utilities.governed_uploads.get_governed_status",
      args: {
        doctype: "Employee",
        name: frm.doc.name,
        fieldname,
      },
    }).then((res) => {
      const governed = res?.message?.governed ? __("Governed ✅") : __("Governed ❌");
      const base = __("Use the Upload Employee Image action to attach a governed file.");
      frm.set_df_property(fieldname, "description", `${base} ${governed}`);
    });
  },

  // ------------------------------------------------------------
  // Actions
  // ------------------------------------------------------------

  create_user(frm) {
    if (!frm.doc.employee_professional_email) {
      frappe.throw(__("Please enter Professional Email"));
    }

    frappe.call({
      method: "ifitwala_ed.hr.doctype.employee.employee.create_user",
      args: { employee: frm.doc.name, email: frm.doc.employee_professional_email },
      callback(r) {
        frm.set_value("user_id", r.message);
      },
    });
  },

  school(frm) {
    // Keep behavior but ensure server efficiency: only fetch when needed.
    if (!frm.doc.school) return;

    frappe.call({
      method: "frappe.client.get_value",
      args: {
        doctype: "School",
        filters: { name: frm.doc.school },
        fieldname: ["organization"],
      },
      callback(r) {
        const org = r?.message?.organization;
        if (!org) return;

        // Only set if different to avoid dirtying the doc unnecessarily
        if (frm.doc.organization !== org) {
          frm.set_value({ organization: org });
        }
      },
    });
  },

  employee_salutation(frm) {
    if (!frm.doc.employee_salutation) return;

    const map = {
      Mr: "Male",
      Mrs: "Female",
      Ms: "Female",
      Miss: "Female",
      Master: "Male",
      Madam: "Female",
    };

    const gender = map[frm.doc.employee_salutation];
    if (gender && frm.doc.employee_gender !== gender) {
      frm.set_value("employee_gender", gender);
    }
  },
});

// ------------------------------------------------------------
// Private helpers (namespaced, no globals)
// ------------------------------------------------------------

/**
 * Lock the rendered Contact/Address UI so it behaves as "display-only".
 *
 * Why this approach:
 * - You want the renderer because it’s convenient and consistent.
 * - But you do NOT want Employee to be a second editing surface.
 * - The safest enforcement is to disable the "Add/Edit" affordances here
 *   and push edits to Contact via the button.
 *
 * This is intentionally DOM-level because the stock renderer is UI-driven.
 */
ifitwala_ed.hr._lock_contact_address_ui = function (frm) {
  // Defensive: wrapper may not exist in some render states
  const $wrapper = $(frm.wrapper);
  if (!$wrapper?.length) return;

  // The address/contact renderer typically injects buttons/links like:
  // - "Add Address", "Edit", "New Contact", etc.
  // Classnames can vary across Frappe versions, so we match by text as a fallback.
  // This stays localized to Employee and is easy to adjust if upstream UI changes.

  const blockedTexts = new Set([
    "Add Address",
    "New Address",
    "Edit Address",
    "Add Contact",
    "New Contact",
    "Edit Contact",
    "Edit",
    "New",
    "Add",
  ]);

  // 1) Disable common button/link affordances within the address/contact section.
  // We scope by the standard containers used by the renderer when present.
  const $sections = $wrapper.find(
    ".address-box, .contact-box, .addresses, .contacts, .address_html, .contact_html"
  );

  const $scope = $sections.length ? $sections : $wrapper;

  $scope.find("button, a").each(function () {
    const $el = $(this);
    const label = ($el.text() || "").trim();

    if (!label) return;
    if (!blockedTexts.has(label)) return;

    // Keep it visible but inert (signals "view-only" rather than "missing feature").
    $el
      .addClass("disabled")
      .attr("disabled", "disabled")
      .attr("aria-disabled", "true")
      .css({ "pointer-events": "none", opacity: 0.55 });
  });

  // 2) Optional: Add a tiny helper hint near the section header (once).
  // This is user-friendly and prevents “why can’t I edit here?” confusion.
  if (!$scope.find(".if-contact-readonly-hint").length) {
    const hint = $(
      `<div class="if-contact-readonly-hint text-muted" style="margin-top:6px;">
        ${__("Contact details are managed in the Contact record. Use the “Contact” button above.")}
      </div>`
    );

    // Insert after first header-like element if present, else prepend.
    const $header = $scope.find("h4, .section-head, .form-section .section-title").first();
    if ($header.length) {
      $header.after(hint);
    } else {
      $scope.prepend(hint);
    }
  }
};
