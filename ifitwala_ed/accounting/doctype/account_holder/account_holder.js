frappe.ui.form.on("Account Holder", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("View Students"), function() {
				frappe.route_options = {
					account_holder: frm.doc.name,
				};
				frappe.set_route("List", "Student");
			});
		}

		frm.trigger("render_billing_contact_summary");
	},

	render_billing_contact_summary(frm) {
		const field = frm.get_field("billing_contact_summary");
		if (!field?.$wrapper?.length) {
			return;
		}

		if (frm.is_new()) {
			field.$wrapper.html("");
			return;
		}

		frappe.call({
			method: "ifitwala_ed.accounting.account_holder_contacts.get_account_holder_billing_contact_summary",
			args: { account_holder: frm.doc.name },
		}).then((res) => {
			const summary = res?.message || {};
			field.$wrapper.html(buildBillingContactSummaryHtml(summary));
		}).catch((err) => {
			field.$wrapper.html(
				`<div class="text-muted small">${escapeBillingHtml(err?.message || __("Unable to load billing contacts."))}</div>`
			);
		});
	},
});

function buildBillingContactSummaryHtml(summary) {
	const contacts = Array.isArray(summary?.contacts) ? summary.contacts : [];
	if (!contacts.length) {
		return `
			<div class="if-billing-contact-panel" style="${PANEL_STYLE}">
				<div class="text-muted small">${escapeBillingHtml(__("No billing contacts linked."))}</div>
			</div>
		`;
	}

	return `
		<div class="if-billing-contact-panel" style="${PANEL_STYLE}">
			<div style="display: grid; gap: 10px;">
				${contacts.map((contact) => buildBillingContactRow(contact)).join("")}
			</div>
		</div>
	`;
}

function buildBillingContactRow(contact) {
	const name = contact.guardian_name || contact.guardian || "";
	const relation = contact.relation ? ` · ${escapeBillingHtml(contact.relation)}` : "";
	const source = contact.source_student_name
		? `<div class="small text-muted">${escapeBillingHtml(contact.source_student_name)}</div>`
		: "";
	const primary = billingCint(contact.is_primary)
		? `<span class="indicator-pill green" style="margin-left: 6px;">${escapeBillingHtml(__("Primary"))}</span>`
		: "";
	const email = contact.email_display || contact.email_masked || __("No email");
	const phone = contact.phone_display || contact.phone_masked || __("No phone");

	return `
		<div class="if-billing-contact-row" style="${ROW_STYLE}">
			<div>
				<div style="font-weight: 600;">
					${escapeBillingHtml(name)}${relation}${primary}
				</div>
				${source}
			</div>
			<div style="display: grid; gap: 6px;">
				<div class="small">
					<span class="text-muted">${escapeBillingHtml(__("Email"))}:</span>
					<span>${escapeBillingHtml(email)}</span>
				</div>
				<div class="small">
					<span class="text-muted">${escapeBillingHtml(__("Phone"))}:</span>
					<span>${escapeBillingHtml(phone)}</span>
				</div>
			</div>
		</div>
	`;
}

function billingCint(value) {
	return parseInt(value || 0, 10) || 0;
}

function escapeBillingHtml(value) {
	return frappe.utils.escape_html(String(value || ""));
}

const PANEL_STYLE = [
	"padding: 12px",
	"border: 1px solid var(--border-color)",
	"border-radius: var(--border-radius-md)",
	"background: var(--fg-color, #fff)",
].join("; ");

const ROW_STYLE = [
	"display: grid",
	"grid-template-columns: minmax(180px, 1fr) minmax(220px, 1fr)",
	"gap: 12px",
	"padding: 10px",
	"border-radius: var(--border-radius-sm)",
	"background: var(--control-bg, #f7f7f7)",
].join("; ");
