// ifitwala_ed/school_site/doctype/website_story/website_story.js

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

function normalizePropsBuilder(builder) {
	if (!builder) return null;
	const openForRow =
		typeof builder.openForRow === "function"
			? builder.openForRow.bind(builder)
			: typeof builder.open === "function"
				? ({ frm, row }) =>
						builder.open({
							frm,
							cdt: row.doctype || "School Website Page Block",
							cdn: row.name,
							blockType: row.block_type
						})
				: null;
	if (!openForRow) return null;
	return {
		openForRow,
		openAddBlock: typeof builder.openAddBlock === "function" ? builder.openAddBlock.bind(builder) : null
	};
}

function getPropsBuilder() {
	return new Promise((resolve) => {
		const existing = normalizePropsBuilder(window.ifitwalaEd && window.ifitwalaEd.websitePropsBuilder);
		if (existing) {
			resolve(existing);
			return;
		}

		frappe.require("/assets/ifitwala_ed/js/website_props_builder.js", () => {
			const loaded = normalizePropsBuilder(window.ifitwalaEd && window.ifitwalaEd.websitePropsBuilder);
			if (!loaded) {
				frappe.msgprint(__("Props Builder is not available. Please refresh the page."));
				resolve(null);
				return;
			}
			resolve(loaded);
		});
	});
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

			const previewUrl = `${getPreviewUrl(`/${schoolSlug}/stories/${frm.doc.slug}`)}?preview=1`;
			window.open(previewUrl, "_blank");
		});

		frm.add_custom_button(__("Add Block"), async () => {
			const builder = await getPropsBuilder();
			if (!builder) return;
			if (typeof builder.openAddBlock !== "function") {
				frappe.msgprint(
					__("Add Block requires the latest Props Builder assets. Run bench build and hard refresh.")
				);
				return;
			}
			builder.openAddBlock({ frm, childTableField: "blocks" });
		});

		frm.add_custom_button(__("Edit Block Props"), async () => {
			const builder = await getPropsBuilder();
			if (!builder) return;
			const row = getSelectedBlockRow(frm);
			if (!row) return;
			builder.openForRow({ frm, row });
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
