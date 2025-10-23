// Copyright (c) 2024, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/curriculum/doctype/program/program.js

frappe.ui.form.on("Program", {
	onload(frm) {
		// Filter the child "course" link in the "courses" table
		frm.set_query("course", "courses", function (doc, cdt, cdn) {
			const picked = (doc.courses || [])
				.filter(r => r.course)
				.map(r => r.course);

			return {
				filters: [
					["Course", "name", "not in", picked],   // no duplicates
					["Course", "status", "=", "Active"]     // only Active
				]
			};
		});
	},

	onload_post_render(frm) {
		// keep your multiple add UX
		frm.get_field("courses").grid.set_multiple_add("course");

		// --- NEW: add the blue button on the Assessment Categories grid toolbar ---
		const grid = frm.fields_dict?.assessment_categories?.grid;
		if (!grid || frm.__inherit_btn_added) return;

		const $btn = grid.add_custom_button(__("Inherit from Parent"), async () => {
			if (!frm.doc.parent_program) {
				frappe.msgprint({
					title: __("Missing Parent Program"),
					indicator: "red",
					message: __("Set a Parent Program first, then try again.")
				});
				return;
			}

			// Confirm overwrite if there are existing rows
			let ok_to_overwrite = true;
			if ((frm.doc.assessment_categories || []).length > 0) {
				ok_to_overwrite = await new Promise(resolve => {
					frappe.confirm(
						__("This will replace current Assessment Categories with the parent's list. Continue?"),
						() => resolve(true),
						() => resolve(false)
					);
				});
			}
			if (!ok_to_overwrite) return;

			frappe.call({
				method: "ifitwala_ed.curriculum.doctype.program.program.inherit_assessment_categories",
				freeze: true,
				args: {
					program: frm.doc.name,
					overwrite: 1
				},
				callback: (r) => {
					if (r?.message) {
						const { added, parent, total } = r.message;
						// Reload just the child table field to avoid a full refresh
						frm.reload_doc().then(() => {
							frm.refresh_field("assessment_categories");
							frappe.show_alert({
								indicator: "green",
								message: __(
									"Imported {0} categories from <b>{1}</b>.",
									[added, parent]
								)
							});
						});
					}
				}
			});
		});

		// Make it primary blue (Bootstrap primary)
		$btn.addClass("btn-primary");

		frm.__inherit_btn_added = true;
	}
});


// to filter out courses that have already been picked out in the program.
frappe.ui.form.on("Program Course", {
});
