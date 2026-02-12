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

const BLOCK_REGISTRY_METHOD_GET_ALLOWED =
	"ifitwala_ed.website.block_registry.get_allowed_block_types_for_builder";
const SEO_ASSISTANT_METHOD =
	"ifitwala_ed.website.seo_checks.get_seo_assistant_report";

function normalizeBlockTypes(value) {
	if (!Array.isArray(value)) return [];
	return [...new Set(value.map((entry) => String(entry || "").trim()).filter(Boolean))];
}

async function fetchAllowedBlockTypes() {
	const res = await frappe.call({
		method: BLOCK_REGISTRY_METHOD_GET_ALLOWED,
		args: {
			parent_doctype: "Website Story"
		}
	});
	return normalizeBlockTypes(res && res.message);
}

function applyAllowedBlockTypesToGrid(frm, allowedTypes) {
	const grid = frm.fields_dict && frm.fields_dict.blocks && frm.fields_dict.blocks.grid;
	if (!grid) return;
	grid.update_docfield_property("block_type", "options", allowedTypes.join("\n"));
	frm.refresh_field("blocks");
}

function updateDisallowedBlockWarning(frm, allowedTypes) {
	if (typeof frm.set_intro !== "function") return;
	const allowedSet = new Set(allowedTypes);
	const disallowed = [
		...new Set(
			(frm.doc.blocks || [])
				.map((row) => String(row.block_type || "").trim())
				.filter((blockType) => blockType && !allowedSet.has(blockType))
		)
	];
	if (!disallowed.length) {
		frm.set_intro("");
		return;
	}
	frm.set_intro(
		__(
			"Some existing blocks are not allowed for Website Story: {0}. Replace them before saving.",
			[disallowed.join(", ")]
		),
		"orange"
	);
}

async function syncAllowedBlockTypes(frm) {
	try {
		const allowedTypes = await fetchAllowedBlockTypes();
		frm.__iwAllowedBlockTypes = allowedTypes;
		applyAllowedBlockTypesToGrid(frm, allowedTypes);
		updateDisallowedBlockWarning(frm, allowedTypes);
		return allowedTypes;
	} catch (err) {
		frm.__iwAllowedBlockTypes = [];
		frappe.msgprint(__("Unable to load allowed block types for Website Story."));
		return [];
	}
}

function setBaseDashboardBanners(frm, banners) {
	frm.__iwBaseDashboardBanners = Array.isArray(banners) ? banners : [];
	renderDashboardHeadline(frm);
}

function setSeoChecks(frm, checks) {
	frm.__iwSeoChecks = Array.isArray(checks) ? checks : [];
	renderDashboardHeadline(frm);
}

function renderDashboardHeadline(frm) {
	if (!frm.dashboard || !frm.dashboard.set_headline) return;

	const baseBanners = Array.isArray(frm.__iwBaseDashboardBanners)
		? frm.__iwBaseDashboardBanners
		: [];
	const seoChecks = Array.isArray(frm.__iwSeoChecks) ? frm.__iwSeoChecks : [];

	if (!baseBanners.length && !seoChecks.length) {
		frm.dashboard.set_headline("");
		return;
	}

	const sections = [];
	if (baseBanners.length) {
		const baseHtml = baseBanners.map((msg) => `• ${frappe.utils.escape_html(msg)}`).join("<br>");
		sections.push(`<span class="text-warning">${baseHtml}</span>`);
	}

	if (seoChecks.length) {
		const seoHtml = seoChecks
			.map((check) => {
				const severity = String(check.severity || "").toLowerCase();
				const klass = severity === "error" ? "text-danger" : "text-warning";
				const tag = severity === "error" ? "[SEO ERROR]" : "[SEO WARN]";
				return `<span class="${klass}">• ${frappe.utils.escape_html(tag)} ${frappe.utils.escape_html(
					check.message || ""
				)}</span>`;
			})
			.join("<br>");
		sections.push(
			`<span><strong>${frappe.utils.escape_html(__("SEO Assistant"))}</strong><br>${seoHtml}</span>`
		);
	}

	frm.dashboard.set_headline(sections.join("<br><br>"));
}

function getSeoPayload(frm) {
	const blocks = (frm.doc.blocks || []).map((row) => ({
		block_type: row.block_type || "",
		order: row.order,
		idx: row.idx,
		is_enabled: row.is_enabled,
		props: row.props || ""
	}));
	return {
		doctype: frm.doctype,
		name: frm.doc.name || null,
		school: frm.doc.school || null,
		title: frm.doc.title || null,
		slug: frm.doc.slug || null,
		seo_profile: frm.doc.seo_profile || null,
		blocks
	};
}

async function refreshSeoAssistant(frm, { showErrorToast = false } = {}) {
	try {
		const res = await frappe.call({
			method: SEO_ASSISTANT_METHOD,
			args: {
				parent_doctype: "Website Story",
				doc_json: JSON.stringify(getSeoPayload(frm))
			}
		});
		const report = res && res.message ? res.message : {};
		const checks = Array.isArray(report.checks) ? report.checks : [];
		setSeoChecks(frm, checks);
		return report;
	} catch (err) {
		setSeoChecks(frm, []);
		if (showErrorToast) {
			frappe.msgprint(__("Unable to compute SEO checks right now."));
		}
		return null;
	}
}

frappe.ui.form.on("Website Story", {
	refresh(frm) {
		frm.clear_custom_buttons();
		syncAllowedBlockTypes(frm);
		refreshSeoAssistant(frm);

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
			const allowedTypes = await syncAllowedBlockTypes(frm);
			if (!allowedTypes.length) {
				frappe.msgprint(__("No block types are configured for Website Story."));
				return;
			}
			builder.openAddBlock({ frm, childTableField: "blocks", allowedTypes });
		});

		frm.add_custom_button(__("SEO Check"), async () => {
			await refreshSeoAssistant(frm, { showErrorToast: true });
			frappe.show_alert({ message: __("SEO checks refreshed."), indicator: "green" });
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
			setBaseDashboardBanners(frm, banners);
		}
	},

	seo_profile(frm) {
		refreshSeoAssistant(frm);
	},

	title(frm) {
		refreshSeoAssistant(frm);
	},

	blocks_add(frm) {
		refreshSeoAssistant(frm);
	},

	blocks_remove(frm) {
		refreshSeoAssistant(frm);
	}
});
