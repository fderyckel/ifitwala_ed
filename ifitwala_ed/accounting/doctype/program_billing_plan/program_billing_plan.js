frappe.ui.form.on("Program Billing Plan", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Generate Billing Schedules"), async () => {
				const r = await frappe.call(
					"ifitwala_ed.accounting.doctype.program_billing_plan.program_billing_plan.generate_billing_schedules",
					{ program_billing_plan: frm.doc.name }
				);
				const message = r.message || {};
				frappe.msgprint(
					__("Generated or refreshed {0} billing schedules.", [message.schedule_names?.length || 0])
				);
			});
		}
	},
});
