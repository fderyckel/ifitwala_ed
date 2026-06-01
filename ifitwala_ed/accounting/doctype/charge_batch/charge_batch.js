const CHARGE_BATCH_PROGRESS_EVENT = "charge_batch_invoice_generation";
const CHARGE_BATCH_DONE_EVENT = "charge_batch_invoice_generation_done";

function chargeBatchCounts(frm) {
	const rows = frm.doc.students || [];
	return {
		ready: rows.filter(row => row.status === "Ready").length,
		blocked: rows.filter(row => row.status === "Blocked").length,
		created: rows.filter(row => row.status === "Charge Created").length,
		invoiced: rows.filter(row => row.status === "Invoiced").length,
		cancelled: rows.filter(row => row.status === "Cancelled").length,
		total: rows.length,
	};
}

function escapeHtml(value) {
	if (frappe.utils?.escape_html) {
		return frappe.utils.escape_html(String(value || ""));
	}
	return String(value || "")
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&#039;");
}

function routeLink(doctype, name, label) {
	if (!name) {
		return "";
	}
	return `<a href="#Form/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}">${escapeHtml(label || name)}</a>`;
}

function renderHeadline(frm) {
	if (!frm.dashboard?.set_headline) {
		return;
	}
	const counts = chargeBatchCounts(frm);
	const generation = frm.doc.invoice_generation_status || "Not Queued";
	const progress = frm.doc.invoice_generation_progress ? ` ${escapeHtml(frm.doc.invoice_generation_progress)}` : "";
	frm.dashboard.set_headline(
		`<span class="text-muted">${escapeHtml(__("Students"))}: ${counts.total}. ` +
		`${escapeHtml(__("Ready"))}: ${counts.ready}. ` +
		`${escapeHtml(__("Blocked"))}: ${counts.blocked}. ` +
		`${escapeHtml(__("Charge Created"))}: ${counts.created}. ` +
		`${escapeHtml(__("Invoiced"))}: ${counts.invoiced}. ` +
		`${escapeHtml(__("Generation"))}: ${escapeHtml(generation)}${progress}.</span>`
	);
}

function openRowsPreview(frm, statusFilter = null) {
	const rows = (frm.doc.students || []).filter(row => !statusFilter || row.status === statusFilter);
	const body = rows.length
		? rows.map(row => {
			const issue = row.issue ? `<div class="text-danger small">${escapeHtml(row.issue)}</div>` : "";
			const links = [
				routeLink("Student", row.student, row.student_name || row.student),
				routeLink("Account Holder", row.account_holder, row.account_holder),
				routeLink("Billable Charge", row.billable_charge, row.billable_charge),
				routeLink("Sales Invoice", row.sales_invoice, row.sales_invoice),
			].filter(Boolean).join(" | ");
			return `
				<tr>
					<td>${escapeHtml(row.status || "")}${issue}</td>
					<td>${links || escapeHtml(row.student || "")}</td>
				</tr>
			`;
		}).join("")
		: `<tr><td colspan="2" class="text-muted">${escapeHtml(__("No rows matched this view."))}</td></tr>`;

	const dialog = new frappe.ui.Dialog({
		title: statusFilter ? __("Charge Batch Rows: {0}", [statusFilter]) : __("Charge Batch Rows"),
		fields: [{ fieldtype: "HTML", fieldname: "rows_html" }],
	});
	dialog.get_field("rows_html").$wrapper.html(`
		<div style="max-height: 60vh; overflow: auto;">
			<table class="table table-bordered table-sm">
				<thead>
					<tr>
						<th style="width: 35%;">${escapeHtml(__("Status"))}</th>
						<th>${escapeHtml(__("Links"))}</th>
					</tr>
				</thead>
				<tbody>${body}</tbody>
			</table>
		</div>
	`);
	dialog.show();
}

async function ensureSaved(frm) {
	if (frm.is_new() || frm.is_dirty()) {
		await frm.save();
	}
}

function openAccountHolderTool(frm) {
	frappe.route_options = {
		organization: frm.doc.organization,
	};
	frappe.new_doc("Student Account Holder Tool");
}

function bindRealtime(frm) {
	if (frm.__charge_batch_realtime_bound) {
		return;
	}

	frappe.realtime.on(CHARGE_BATCH_PROGRESS_EVENT, data => {
		if (!data || data.charge_batch !== frm.doc.name) {
			return;
		}
		frappe.show_progress(
			data.progress_label || __("Generating draft invoices"),
			data.progress?.[0] || 0,
			data.progress?.[1] || 0
		);
	});

	frappe.realtime.on(CHARGE_BATCH_DONE_EVENT, async data => {
		if (!data || data.charge_batch !== frm.doc.name) {
			return;
		}
		frappe.hide_msgprint(true);
		await frm.reload_doc();
		if (data.ok) {
			const result = data.result || {};
			frappe.msgprint({
				title: __("Draft Invoice Generation Finished"),
				message: __("Created {0} draft invoice(s) covering {1} charge(s).", [
					result.invoice_count || 0,
					result.billable_charge_count || 0,
				]),
				indicator: "green",
			});
		} else {
			frappe.msgprint({
				title: __("Draft Invoice Generation Failed"),
				message: escapeHtml(data.error || __("Open the Charge Batch to review the failure.")),
				indicator: "red",
			});
		}
	});

	frm.__charge_batch_realtime_bound = true;
}

frappe.ui.form.on("Charge Batch", {
	refresh(frm) {
		renderHeadline(frm);
		bindRealtime(frm);

		if (frm.is_new() || frm.doc.status === "Cancelled") {
			return;
		}

		const counts = chargeBatchCounts(frm);
		const generation = frm.doc.invoice_generation_status || "Not Queued";
		const generationRunning = ["Queued", "Processing"].includes(generation);

		frm.add_custom_button(__("Preview Rows"), () => openRowsPreview(frm), __("Review"));
		if (counts.blocked) {
			frm.add_custom_button(__("Show Blocked Rows"), () => openRowsPreview(frm, "Blocked"), __("Review"));
			frm.add_custom_button(__("Open Account Holder Tool"), () => openAccountHolderTool(frm), __("Fix"));
		}

		frm.add_custom_button(__("Resolve Students"), async () => {
			await ensureSaved(frm);
			const r = await frappe.call(
				"ifitwala_ed.accounting.doctype.charge_batch.charge_batch.resolve_students",
				{ charge_batch: frm.doc.name }
			);
			const message = r.message || {};
			frappe.msgprint(
				__("Ready: {0}. Blocked: {1}. Invoiced: {2}.", [
					message.ready_count || 0,
					message.blocked_count || 0,
					message.invoiced_count || 0,
				])
			);
			await frm.reload_doc();
		});

		if (frm.doc.status !== "Invoiced" && !generationRunning) {
			frm.add_custom_button(__("Create Pending Charges"), async () => {
				await ensureSaved(frm);
				const r = await frappe.call(
					"ifitwala_ed.accounting.doctype.charge_batch.charge_batch.create_pending_charges",
					{ charge_batch: frm.doc.name }
				);
				const message = r.message || {};
				frappe.msgprint(
					__("Created {0} charge(s), updated {1}, skipped {2}.", [
						message.created_count || 0,
						message.updated_count || 0,
						message.skipped_count || 0,
					])
				);
				await frm.reload_doc();
			});

			frm.add_custom_button(__("Generate Draft Invoices"), async () => {
				if (chargeBatchCounts(frm).blocked) {
					openRowsPreview(frm, "Blocked");
					frappe.msgprint(__("Resolve blocked student rows before generating draft invoices."));
					return;
				}
				await ensureSaved(frm);
				const r = await frappe.call(
					"ifitwala_ed.accounting.doctype.charge_batch.charge_batch.generate_draft_invoices",
					{ charge_batch: frm.doc.name }
				);
				const message = r.message || {};
				if (message.queued) {
					frappe.msgprint({
						title: __("Draft Invoice Generation Queued"),
						message: message.message || __("Draft invoice generation was queued."),
						indicator: "blue",
					});
					await frm.reload_doc();
					return;
				}
				frappe.msgprint(
					__("Created {0} draft invoice(s) covering {1} charge(s).", [
						message.invoice_count || 0,
						message.billable_charge_count || 0,
					])
				);
				await frm.reload_doc();
			});
		}
	},
});
