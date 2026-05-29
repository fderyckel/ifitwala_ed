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
			bindBillingContactRevealActions(frm, field.$wrapper);
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
				${contacts.map((contact) => buildBillingContactRow(contact, Boolean(summary.can_reveal))).join("")}
			</div>
		</div>
	`;
}

function buildBillingContactRow(contact, canReveal) {
	const name = contact.guardian_name || contact.guardian || "";
	const relation = contact.relation ? ` · ${escapeBillingHtml(contact.relation)}` : "";
	const source = contact.source_student_name
		? `<div class="small text-muted">${escapeBillingHtml(contact.source_student_name)}</div>`
		: "";
	const primary = billingCint(contact.is_primary)
		? `<span class="indicator-pill green" style="margin-left: 6px;">${escapeBillingHtml(__("Primary"))}</span>`
		: "";
	const email = contact.email_masked || __("No email");
	const phone = contact.phone_masked || __("No phone");
	const revealEmail = canReveal && contact.has_email
		? buildRevealButton(contact.name, "email", __("Reveal email"))
		: "";
	const revealPhone = canReveal && contact.has_phone
		? buildRevealButton(contact.name, "phone", __("Reveal phone"))
		: "";

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
					${revealEmail}
				</div>
				<div class="small">
					<span class="text-muted">${escapeBillingHtml(__("Phone"))}:</span>
					<span>${escapeBillingHtml(phone)}</span>
					${revealPhone}
				</div>
			</div>
		</div>
	`;
}

function buildRevealButton(rowName, channelType, label) {
	return `
		<button
			type="button"
			class="btn btn-xs btn-default"
			style="margin-left: 6px;"
			data-reveal-billing-contact="${escapeBillingHtml(rowName)}"
			data-channel-type="${escapeBillingHtml(channelType)}"
		>
			${escapeBillingHtml(label)}
		</button>
	`;
}

function bindBillingContactRevealActions(frm, wrapper) {
	wrapper.find("[data-reveal-billing-contact]").on("click", function() {
		const $button = $(this);
		const billingContact = String($button.attr("data-reveal-billing-contact") || "").trim();
		const channelType = String($button.attr("data-channel-type") || "").trim();
		if (!billingContact || !channelType) {
			frappe.msgprint(__("Billing contact selection is missing. Refresh and try again."));
			return;
		}

		frappe.call({
			method: "ifitwala_ed.accounting.account_holder_contacts.reveal_account_holder_billing_contact_value",
			args: {
				account_holder: frm.doc.name,
				billing_contact: billingContact,
				channel_type: channelType,
			},
			freeze: true,
			freeze_message: __("Loading billing contact..."),
		}).then((res) => {
			const payload = res?.message || {};
			frappe.msgprint({
				title: __("Billing Contact"),
				message: `<div style="font-size: 14px;">${escapeBillingHtml(payload.value || "")}</div>`,
			});
		}).catch((err) => {
			frappe.msgprint(err?.message || __("Unable to reveal billing contact."));
		});
	});
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
