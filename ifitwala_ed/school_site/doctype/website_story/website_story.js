// ifitwala_ed/school_site/doctype/website_story/website_story.js

async function getFieldValue(doctype, name, fieldname) {
	if (!name) return null;
	const res = await frappe.db.get_value(doctype, name, fieldname);
	return res && res.message ? res.message[fieldname] : null;
}

frappe.ui.form.on("Website Story", {
	refresh(frm) {
		frm.clear_custom_buttons();

		frm.add_custom_button(__("Preview"), async () => {
			if (!frm.doc.school || !frm.doc.slug) {
				frappe.msgprint(__("Select a School and slug to preview."));
				return;
			}

			const schoolSlug = await getFieldValue("School", frm.doc.school, "website_slug");
			if (!schoolSlug) {
				frappe.msgprint(__("School must have a website slug before preview."));
				return;
			}

			const previewUrl = `${frappe.utils.get_url(`/${schoolSlug}/stories/${frm.doc.slug}`)}?preview=1`;
			window.open(previewUrl, "_blank");
		});

		if (frm.dashboard && frm.dashboard.set_headline && !frm.doc.seo_profile) {
			frm.dashboard.set_headline(
				`<span class="text-warning">${frappe.utils.escape_html(
					__("SEO fallback in use. Link an SEO Profile for full control.")
				)}</span>`
			);
		}
	}
});
