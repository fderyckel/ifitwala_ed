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

function validatePreviewBlockPropsJson(frm) {
	const enabledRows = (frm.doc.blocks || []).filter((row) => Boolean(Number(row.is_enabled || 0)));
	for (const row of enabledRows) {
		const raw = String(row.props || "").trim();
		if (!raw) continue;
		try {
			JSON.parse(raw);
		} catch (err) {
			const rowLabel = String(row.idx || "?");
			const blockLabel = (row.block_type || "").trim() || __("Unknown block");
			const message = err && err.message ? err.message : String(err);
			frappe.msgprint(
				__("Invalid Props JSON in Blocks row {0} ({1}): {2}", [rowLabel, blockLabel, message])
			);
			return false;
		}
	}
	return true;
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
			parent_doctype: "Program Website Profile"
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
			"Some existing blocks are not allowed for Program Website Profile: {0}. Replace them before saving.",
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
		frappe.msgprint(__("Unable to load allowed block types for Program Website Profile."));
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
		program: frm.doc.program || null,
		intro_text: frm.doc.intro_text || null,
		seo_profile: frm.doc.seo_profile || null,
		blocks
	};
}

async function refreshSeoAssistant(frm, { showErrorToast = false } = {}) {
	try {
		const res = await frappe.call({
			method: SEO_ASSISTANT_METHOD,
			args: {
				parent_doctype: "Program Website Profile",
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

frappe.ui.form.on("Program Website Profile", {
	refresh(frm) {
		frm.clear_custom_buttons();
		syncAllowedBlockTypes(frm);
		refreshSeoAssistant(frm);

		frm.add_custom_button(__("Preview"), async () => {
			if (!frm.doc.school || !frm.doc.program) {
				frappe.msgprint(__("Select a School and Program to preview."));
				return;
			}

			const hasValidJson = validatePreviewBlockPropsJson(frm);
			if (!hasValidJson) return;

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
			const allowedTypes = await syncAllowedBlockTypes(frm);
			if (!allowedTypes.length) {
				frappe.msgprint(__("No block types are configured for Program Website Profile."));
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
					setBaseDashboardBanners(frm, banners);
				}).catch(() => {
					setBaseDashboardBanners(frm, banners);
				});
			} else if (banners.length) {
				setBaseDashboardBanners(frm, banners);
			} else {
				setBaseDashboardBanners(frm, []);
			}
		}
	},

	seo_profile(frm) {
		refreshSeoAssistant(frm);
	},

	program(frm) {
		refreshSeoAssistant(frm);
	},

	intro_text(frm) {
		refreshSeoAssistant(frm);
	},

	blocks_add(frm) {
		refreshSeoAssistant(frm);
	},

	blocks_remove(frm) {
		refreshSeoAssistant(frm);
	}
});
