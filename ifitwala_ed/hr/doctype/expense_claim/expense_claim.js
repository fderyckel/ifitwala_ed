// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Expense Claim", {
	refresh(frm) {
		frm.trigger("setup_governed_receipt_upload");
	},

	setup_governed_receipt_upload(frm) {
		const tableField = frm.get_field("receipts");

		if (tableField?.grid) {
			tableField.grid.update_docfield_property("file", "read_only", 1);
			tableField.grid.update_docfield_property(
				"file",
				"description",
				get_expense_claim_receipt_file_description()
			);

			tableField.grid.wrapper
				.find(".grid-custom-buttons .expense-claim-upload-receipt-btn")
				.remove();

			const gridButton = tableField.grid.add_custom_button(
				__("Upload Receipt"),
				() => open_expense_claim_receipt_uploader(frm)
			);
			gridButton.addClass("expense-claim-upload-receipt-btn");

			(frm.doc.receipts || []).forEach((row) => {
				const rowName = String(row?.name || "").trim();
				if (rowName) {
					setup_expense_claim_receipt_row(frm, rowName);
				}
			});
		}

		frm.set_df_property(
			"receipts",
			"description",
			__("Use Upload Receipt for governed receipt files. External URLs can still be added manually.")
		);

		frm.remove_custom_button(__("Upload Receipt"), __("Actions"));
		frm.remove_custom_button(__("Upload Receipt"));
		frm.add_custom_button(
			__("Upload Receipt"),
			() => open_expense_claim_receipt_uploader(frm),
			__("Actions")
		);
	},

	receipts_add(frm, cdt, cdn) {
		window.setTimeout(() => {
			setup_expense_claim_receipt_row(frm, cdn);
		}, 0);
	},
});

frappe.ui.form.on("Attached Document", {
	form_render(frm, cdt, cdn) {
		if (frm.doctype !== "Expense Claim") {
			return;
		}
		setup_expense_claim_receipt_row(frm, cdn);
	},
});

async function open_expense_claim_receipt_uploader(frm) {
	try {
		if (frm.is_new() || frm.is_dirty()) {
			await frm.save();
		}
	} catch (error) {
		return;
	}

	if (frm.is_new()) {
		frappe.msgprint({
			title: __("Save Required"),
			indicator: "orange",
			message: __("Save the Expense Claim before uploading receipts."),
		});
		return;
	}

	new frappe.ui.FileUploader({
		method: "ifitwala_ed.api.expense_claim_receipts.upload_expense_claim_receipt",
		args: { expense_claim: frm.doc.name },
		doctype: "Expense Claim",
		docname: frm.doc.name,
		is_private: 1,
		disable_private: true,
		allow_multiple: false,
		on_success() {
			frm.reload_doc();
		},
		on_error() {
			frappe.msgprint(__("Receipt upload failed. Please try again."));
		},
	});
}

function get_expense_claim_receipt_file_description() {
	return __("Use Upload Receipt for governed files. External URLs can still be added manually.");
}

function setup_expense_claim_receipt_row(frm, cdn) {
	const grid = frm.fields_dict.receipts?.grid;
	if (!grid || !cdn) return;

	const gridRow = grid.get_row(cdn);
	const gridForm = gridRow?.grid_form;
	const fileField = get_grid_field(gridForm, "file");
	if (fileField?.df) {
		fileField.df.read_only = 1;
		fileField.df.description = get_expense_claim_receipt_file_description();
		fileField.refresh && fileField.refresh();
	}

	const rowWrapper = grid.grid_rows_by_docname?.[cdn]?.row;
	if (!rowWrapper?.length || rowWrapper.find(".expense-claim-row-upload-receipt-btn").length) {
		return;
	}

	const button = $(
		`<button type="button" class="btn btn-xs btn-default expense-claim-row-upload-receipt-btn">
			${__("Upload Receipt")}
		</button>`
	);
	button.on("click", (event) => {
		event.preventDefault();
		event.stopPropagation();
		void open_expense_claim_receipt_uploader(frm);
	});

	const actions = rowWrapper.find(".row-check, .row-index").last();
	if (actions.length) {
		actions.after(button);
		return;
	}

	rowWrapper.prepend(button);
}

function get_grid_field(gridForm, fieldname) {
	if (!gridForm || !fieldname) return null;

	if (gridForm.fields_dict?.[fieldname]) {
		return gridForm.fields_dict[fieldname];
	}

	return (gridForm.fields || []).find((field) => field?.df?.fieldname === fieldname) || null;
}
