const GET_BILLING_PLAN_CONTEXT =
	"ifitwala_ed.accounting.doctype.billing_run.billing_run.get_billing_plan_context";
const GENERATE_DRAFT_INVOICES =
	"ifitwala_ed.accounting.doctype.billing_run.billing_run.generate_draft_invoices";

async function ensureSaved(frm) {
	if (frm.is_new() || frm.is_dirty()) {
		await frm.save();
	}
}

async function hydrate_context_from_billing_plan(frm) {
	if (!frm.doc.billing_plan) {
		return;
	}

	const response = await frappe.call({
		method: GET_BILLING_PLAN_CONTEXT,
		args: { billing_plan: frm.doc.billing_plan },
	});
	const context = response.message || {};
	if (!context.is_active) {
		frappe.msgprint(__("Select an active Program Billing Plan before generating a Billing Run."));
		return;
	}

	const values = {
		organization: context.organization || null,
		program_offering: context.program_offering || null,
		academic_year: context.academic_year || null,
	};
	const changedValues = Object.fromEntries(
		Object.entries(values).filter(([fieldname, value]) => frm.doc[fieldname] !== value)
	);
	if (Object.keys(changedValues).length) {
		await frm.set_value(changedValues);
	}
}

frappe.ui.form.on("Billing Run", {
	onload(frm) {
		hydrate_context_from_billing_plan(frm).catch((error) => {
			frappe.msgprint(error?.message || __("Unable to load Program Billing Plan context."));
		});
	},

	refresh(frm) {
		if (!frm.is_new() && frm.doc.status === "Draft") {
			frm.add_custom_button(__("Generate Draft Invoices"), async () => {
				await ensureSaved(frm);
				const r = await frappe.call(GENERATE_DRAFT_INVOICES, { billing_run: frm.doc.name });
				const message = r.message || {};
				frappe.msgprint(
					__(
						"Created {0} draft invoices covering {1} billing rows.",
						[message.invoice_count || 0, message.billing_row_count || 0]
					)
				);
				await frm.reload_doc();
			});
		}
	},

	billing_plan(frm) {
		hydrate_context_from_billing_plan(frm).catch((error) => {
			frappe.msgprint(error?.message || __("Unable to load Program Billing Plan context."));
		});
	},
});
