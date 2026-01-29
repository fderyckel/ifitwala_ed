// ifitwala_ed/school_site/doctype/school_website_page/school_website_page.js

frappe.ui.form.on("School Website Page", {
	refresh(frm) {
		frm.clear_custom_buttons();

		if (frm.doc.full_route) {
			frm.add_custom_button(__("Preview"), () => {
				const previewUrl = `${frappe.utils.get_url(frm.doc.full_route)}?preview=1`;
				window.open(previewUrl, "_blank");
			});
		} else {
			frm.add_custom_button(__("Preview"), () => {
				frappe.msgprint(__("Save the page to generate the full route for preview."));
			});
		}

		if (frm.dashboard && frm.dashboard.set_headline) {
			const banners = [];

			if (!frm.doc.seo_profile && (frm.doc.title || frm.doc.meta_description)) {
				banners.push(__("SEO fallback in use. Link an SEO Profile for full control."));
			} else if (!frm.doc.seo_profile) {
				banners.push(__("Missing SEO Profile and fallback fields."));
			}

			if (frm.doc.school) {
				frappe.db
					.get_value("School", frm.doc.school, ["website_slug", "is_group"])
					.then((res) => {
						const data = res && res.message ? res.message : {};
						const slug = data.website_slug;
						const isGroup = Boolean(parseInt(data.is_group || 0, 10));
						if (!slug || isGroup) {
							banners.push(__("School is not eligible for public website (slug required; groups not public)."));
						}

						if (banners.length) {
							const html = banners.map((msg) => `• ${frappe.utils.escape_html(msg)}`).join("<br>");
							frm.dashboard.set_headline(`<span class="text-warning">${html}</span>`);
						} else {
							frm.dashboard.set_headline("");
						}
					});
			} else if (banners.length) {
				const html = banners.map((msg) => `• ${frappe.utils.escape_html(msg)}`).join("<br>");
				frm.dashboard.set_headline(`<span class="text-warning">${html}</span>`);
			}
		}
	}
});
