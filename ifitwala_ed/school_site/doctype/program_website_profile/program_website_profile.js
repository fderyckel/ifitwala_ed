// ifitwala_ed/school_site/doctype/program_website_profile/program_website_profile.js

function getPreviewUrl(path) {
	if (!path) return "";
	if (path.startsWith("http://") || path.startsWith("https://")) {
		return path;
	}
	if (frappe.utils && typeof frappe.utils.get_url === "function") {
		return frappe.utils.get_url(path);
	}
	if (frappe.urllib && typeof frappe.urllib.get_full_url === "function") {
		return frappe.urllib.get_full_url(path);
	}
	const base =
		frappe.urllib && typeof frappe.urllib.get_base_url === "function"
			? frappe.urllib.get_base_url()
			: window.location.origin;
	if (!base) return path;
	if (path.startsWith("/")) return `${base}${path}`;
	return `${base}/${path}`;
}

async function getFieldValue(doctype, name, fieldname) {
	if (!name) return null;
	const res = await frappe.db.get_value(doctype, name, fieldname);
	return res && res.message ? res.message[fieldname] : null;
}

function getPropsBuilder() {
	const builder = window.ifitwalaEd && window.ifitwalaEd.websitePropsBuilder;
	if (!builder || typeof builder.openForRow !== "function") {
		frappe.msgprint(__("Props Builder is not available. Please refresh the page."));
		return null;
	}
	return builder;
}

function getSelectedBlockRow(frm) {
	const rows = frm.doc.blocks || [];
	if (!rows.length) {
		frappe.msgprint(__("Add at least one block first."));
		return null;
	}

	const selected = (frm.get_selected && frm.get_selected().blocks) || [];
	if (selected.length > 1) {
		frappe.msgprint(__("Select exactly one block row."));
		return null;
	}
	if (selected.length === 1) {
		return rows.find((row) => row.name === selected[0]) || null;
	}
	if (rows.length === 1) {
		return rows[0];
	}

	frappe.msgprint(__("Select one row in Blocks, then click Edit Block Props."));
	return null;
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

			const previewUrl = `${getPreviewUrl(`/${schoolSlug}/programs/${programSlug}`)}?preview=1`;
			window.open(previewUrl, "_blank");
		});

		frm.add_custom_button(__("Edit Block Props"), () => {
			const builder = getPropsBuilder();
			if (!builder) return;
			const row = getSelectedBlockRow(frm);
			if (!row) return;
			builder.openForRow({ frm, row });
		});

		if (frm.dashboard && frm.dashboard.set_headline) {
			const banners = [];

			if (!frm.doc.seo_profile) {
				banners.push(__("SEO fallback in use. Link an SEO Profile for full control."));
			}

			if (frm.doc.program) {
				Promise.all([
					getFieldValue("Program", frm.doc.program, "is_published"),
					getFieldValue("Program", frm.doc.program, "archive")
				]).then(([isPublished, isArchived]) => {
					const published = Boolean(parseInt(isPublished || 0, 10));
					const archived = Boolean(parseInt(isArchived || 0, 10));
					if (archived) {
						banners.push(__("Program is archived and cannot be published."));
					}
					if (!published) {
						banners.push(__("Program is not published; profile will remain draft."));
					}

					if (banners.length) {
						const html = banners
							.map((msg) => `• ${frappe.utils.escape_html(msg)}`)
							.join("<br>");
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
