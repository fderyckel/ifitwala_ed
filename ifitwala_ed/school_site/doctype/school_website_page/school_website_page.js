// ifitwala_ed/school_site/doctype/school_website_page/school_website_page.js

frappe.ui.form.on("School Website Page", {
	refresh(frm) {
		frm.clear_custom_buttons();

		if (frm.doc.route) {
			frm.add_custom_button(__("Preview"), () => {
				const previewUrl = `${frappe.utils.get_url(frm.doc.route)}?preview=1`;
				window.open(previewUrl, "_blank");
			});
		} else {
			frm.add_custom_button(__("Preview"), () => {
				frappe.msgprint(__("Save the page to generate a preview route."));
			});
		}

		if (frm.dashboard && frm.dashboard.set_headline) {
			if (!frm.doc.seo_profile && (frm.doc.title || frm.doc.meta_description)) {
				frm.dashboard.set_headline(
					`<span class="text-warning">${frappe.utils.escape_html(
						__("SEO fallback in use. Link an SEO Profile for full control.")
					)}</span>`
				);
			} else if (!frm.doc.seo_profile) {
				frm.dashboard.set_headline(
					`<span class="text-danger">${frappe.utils.escape_html(
						__("Missing SEO Profile and fallback fields.")
					)}</span>`
				);
			}
		}
	}
});
