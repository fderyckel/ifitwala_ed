// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

function canCreateChargeBatch() {
	return !frappe.model?.can_create || frappe.model.can_create("Charge Batch");
}

async function getActivityBillingDefaults(programOffering) {
	if (!programOffering) {
		return {};
	}
	try {
		const response = await frappe.db.get_value("Program Offering", programOffering, [
			"activity_billable_offering",
			"activity_fee_amount",
			"offering_title",
		]);
		return response?.message || {};
	} catch (error) {
		return {};
	}
}

async function openActivityBookingChargeBatchDialog(frm) {
	const defaults = await getActivityBillingDefaults(frm.doc.program_offering);
	const dialog = new frappe.ui.Dialog({
		title: __("Create Charge Batch"),
		fields: [
			{
				fieldname: "billable_offering",
				fieldtype: "Link",
				label: __("Billable Offering"),
				options: "Billable Offering",
				default: defaults.activity_billable_offering || "",
				reqd: !defaults.activity_billable_offering,
			},
			{
				fieldname: "posting_date",
				fieldtype: "Date",
				label: __("Posting Date"),
				default: frappe.datetime.get_today(),
				reqd: 1,
			},
			{
				fieldname: "due_date",
				fieldtype: "Date",
				label: __("Due Date"),
			},
			{
				fieldname: "payment_terms_template",
				fieldtype: "Link",
				label: __("Payment Terms Template"),
				options: "Payment Terms Template",
			},
			{ fieldtype: "Column Break" },
			{
				fieldname: "default_qty",
				fieldtype: "Float",
				label: __("Default Qty"),
				default: 1,
				reqd: 1,
			},
			{
				fieldname: "default_rate",
				fieldtype: "Currency",
				label: __("Default Rate"),
				default: frm.doc.amount || defaults.activity_fee_amount || 0,
				reqd: !(frm.doc.amount || defaults.activity_fee_amount),
			},
			{
				fieldname: "description",
				fieldtype: "Small Text",
				label: __("Description"),
				default: __("Activity booking fee for {0}", [defaults.offering_title || frm.doc.program_offering]),
			},
		],
		primary_action_label: __("Create Charge Batch"),
		primary_action: async values => {
			if (!values.due_date && !values.payment_terms_template) {
				frappe.msgprint(__("Choose a Due Date or Payment Terms Template."));
				return;
			}
			const response = await frappe.call({
				method: "ifitwala_ed.accounting.charges.source_context.create_charge_batch_from_context",
				args: {
					source_doctype: "Activity Booking",
					source_name: frm.doc.name,
					billable_offering: values.billable_offering,
					posting_date: values.posting_date,
					due_date: values.due_date,
					payment_terms_template: values.payment_terms_template,
					default_qty: values.default_qty,
					default_rate: values.default_rate,
					description: values.description,
				},
				freeze: true,
				freeze_message: __("Creating Charge Batch..."),
			});
			const message = response.message || {};
			dialog.hide();
			if (message.charge_batch) {
				frappe.set_route("Form", "Charge Batch", message.charge_batch);
			}
		},
	});
	dialog.show();
}

frappe.ui.form.on("Activity Booking", {
	refresh(frm) {
		if (
			frm.is_new() ||
			frm.doc.status !== "Confirmed" ||
			frm.doc.sales_invoice ||
			!canCreateChargeBatch()
		) {
			return;
		}

		frm.add_custom_button(
			__("Create Charge Batch"),
			() => {
				openActivityBookingChargeBatchDialog(frm).catch(error => {
					frappe.msgprint(error?.message || __("Unable to create Charge Batch."));
				});
			},
			__("Billing")
		);
	},
});
