// ifitwala_ed/school_site/doctype/school_website_page_block/school_website_page_block.js

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
	return { openForRow };
}

function getPropsBuilder() {
	return new Promise((resolve) => {
		const existing = normalizePropsBuilder(window.ifitwalaEd && window.ifitwalaEd.websitePropsBuilder);
		if (existing) {
			resolve(existing);
			return;
		}
		frappe.require("/assets/ifitwala_ed/js/website_props_builder.js", () => {
			resolve(normalizePropsBuilder(window.ifitwalaEd && window.ifitwalaEd.websitePropsBuilder));
		});
	});
}

function getGridFormField(gridForm, fieldname) {
	if (!gridForm || !fieldname) return null;
	if (typeof gridForm.get_field === "function") {
		return gridForm.get_field(fieldname);
	}
	if (gridForm.fields_dict && gridForm.fields_dict[fieldname]) {
		return gridForm.fields_dict[fieldname];
	}
	return null;
}

frappe.ui.form.on("School Website Page Block", {
	form_render(frm, cdt, cdn) {
		const grid = frm.fields_dict.blocks && frm.fields_dict.blocks.grid;
		if (!grid) return;
		const grid_row = grid.get_row(cdn);
		if (!grid_row || !grid_row.grid_form) return;

		const propsField = getGridFormField(grid_row.grid_form, "props");
		if (!propsField || !propsField.$wrapper) return;
		if (propsField.$wrapper.find(".iw-props-builder-btn").length) return;

		const button = $(
			`<button type="button" class="btn btn-xs btn-default iw-props-builder-btn">` +
				`${__("Edit Props")}</button>`
		);

		button.on("click", async () => {
			const row = locals[cdt][cdn];
			if (!row.block_type) {
				frappe.msgprint(__("Select a block type first."));
				return;
			}
			const builder = await getPropsBuilder();
			if (!builder) {
				frappe.msgprint(__("Props Builder is not available. Please refresh the page."));
				return;
			}
			builder.openForRow({ frm, row });
		});

		propsField.$wrapper.append(button);
	}
});
