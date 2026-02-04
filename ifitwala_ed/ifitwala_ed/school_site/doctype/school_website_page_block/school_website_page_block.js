// ifitwala_ed/school_site/doctype/school_website_page_block/school_website_page_block.js

frappe.ui.form.on("School Website Page Block", {
	form_render(frm, cdt, cdn) {
		const grid = frm.fields_dict.blocks && frm.fields_dict.blocks.grid;
		if (!grid) return;
		const grid_row = grid.get_row(cdn);
		if (!grid_row || !grid_row.grid_form) return;

		const propsField = grid_row.grid_form.get_field("props");
		if (!propsField || !propsField.$wrapper) return;
		if (propsField.$wrapper.find(".iw-props-builder-btn").length) return;

		const button = $(
			`<button type="button" class="btn btn-xs btn-default iw-props-builder-btn">` +
				`${__("Edit Props")}</button>`
		);

		button.on("click", () => {
			const row = locals[cdt][cdn];
			if (!row.block_type) {
				frappe.msgprint(__("Select a block type first."));
				return;
			}
			const builder = window.ifitwalaEd && window.ifitwalaEd.websitePropsBuilder;
			if (!builder || typeof builder.open !== "function") {
				frappe.msgprint(__("Props Builder is not available. Please refresh the page."));
				return;
			}
			builder.open({ frm, cdt, cdn, blockType: row.block_type });
		});

		propsField.$wrapper.append(button);
	}
});
