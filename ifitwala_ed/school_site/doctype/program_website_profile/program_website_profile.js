// ifitwala_ed/school_site/doctype/program_website_profile/program_website_profile.js

async function getFieldValue(doctype, name, fieldname) {
	if (!name) return null;
	const res = await frappe.db.get_value(doctype, name, fieldname);
	return res && res.message ? res.message[fieldname] : null;
}

frappe.ui.form.on("Program Website Profile", {
	refresh(frm) {
		frm.clear_custom_buttons();

		frm.add_custom_button(__("Preview"), async () => {
			if (!frm.doc.school || !frm.doc.program) {
				frappe.msgprint(__("Select a School and Program to preview."));
				return;
			}

			const [schoolSlug, programSlug] = await Promise.all([
				getFieldValue("School", frm.doc.school, "website_slug"),
				getFieldValue("Program", frm.doc.program, "program_slug")
			]);

			if (!schoolSlug || !programSlug) {
				frappe.msgprint(__("School and Program must have slugs before preview."));
				return;
			}

			const previewUrl = `${frappe.utils.get_url(`/${schoolSlug}/programs/${programSlug}`)}?preview=1`;
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
