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

function getBlockSortRank(row) {
	const order = Number(row && row.order);
	if (Number.isFinite(order)) return order;
	const idx = Number(row && row.idx);
	if (Number.isFinite(idx)) return idx;
	return 999999;
}

async function validatePreviewSeoRules(frm) {
	const enabledRows = (frm.doc.blocks || [])
		.filter((row) => Boolean(Number(row.is_enabled || 0)))
		.sort((a, b) => getBlockSortRank(a) - getBlockSortRank(b));

	if (!enabledRows.length) {
		frappe.msgprint(__("Add at least one enabled block before preview."));
		return false;
	}

	const blockTypes = [...new Set(enabledRows.map((row) => (row.block_type || "").trim()).filter(Boolean))];
	if (!blockTypes.length) {
		frappe.msgprint(__("Select a block type for enabled rows before preview."));
		return false;
	}

	let definitionRows = [];
	try {
		definitionRows = await frappe.db.get_list("Website Block Definition", {
			fields: ["block_type", "seo_role"],
			filters: { block_type: ["in", blockTypes] },
			limit_page_length: blockTypes.length
		});
	} catch (err) {
		frappe.msgprint(__("Unable to validate block SEO rules before preview."));
		return false;
	}

	const rolesByType = {};
	(definitionRows || []).forEach((row) => {
		rolesByType[row.block_type] = row.seo_role;
	});

	const missing = blockTypes.filter((blockType) => !rolesByType[blockType]);
	if (missing.length) {
		frappe.msgprint(__("Missing block definitions for: {0}", [missing.join(", ")]));
		return false;
	}

	const ownsH1Count = enabledRows.reduce(
		(count, row) => count + (rolesByType[row.block_type] === "owns_h1" ? 1 : 0),
		0
	);
	if (ownsH1Count !== 1) {
		frappe.msgprint(
			__(
				"Preview requires exactly one enabled H1 owner block (for example Program Intro or Hero). Found {0}.",
				[String(ownsH1Count)]
			)
		);
		return false;
	}

	const firstRole = rolesByType[enabledRows[0].block_type];
	if (firstRole !== "owns_h1") {
		frappe.msgprint(__("The first enabled block must own the H1."));
		return false;
	}

	return true;
}

frappe.ui.form.on("Program Website Profile", {
	refresh(frm) {
		frm.clear_custom_buttons();

		frm.add_custom_button(__("Preview"), async () => {
			if (!frm.doc.school || !frm.doc.program) {
				frappe.msgprint(__("Select a School and Program to preview."));
				return;
			}

			const canPreview = await validatePreviewSeoRules(frm);
			if (!canPreview) return;

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
