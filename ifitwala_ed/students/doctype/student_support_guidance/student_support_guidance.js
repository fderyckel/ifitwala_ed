// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// Copyright (c) 2025
// For license information, please see license.txt

// ifitwala_ed/students/doctype/student_support_guidance/student_support_guidance.js

frappe.ui.form.on("Student Support Guidance", {
	refresh: function (frm) {
		// Render the cached teacher-facing snapshot (server populates snapshot_html)
		if (frm.fields_dict.snapshot_html) {
			const html = frm.doc.snapshot_html || `<div class="text-muted">${__("No guidance yet.")}</div>`;
			frm.fields_dict.snapshot_html.$wrapper.html(html);
		}

		// Dashboard indicators (quick signal for counselors/admins)
		frm.dashboard.clear_headline();
		const hp = cint(frm.doc.high_priority_count || 0);
		const ackn = cint(frm.doc.ack_required_count || 0);
		const st = (frm.doc.status || "").trim();
		if (st) frm.dashboard.add_indicator(__(st), st === "Published" ? "green" : "orange");
		if (hp > 0) frm.dashboard.add_indicator(__("{0} High-priority item(s)", [hp]), "red");
		if (ackn > 0 && st === "Published") frm.dashboard.add_indicator(__("{0} item(s) require acknowledgement", [ackn]), "orange");

		// Only counselors/admins should see publish tools (server still enforces)
		const roles = new Set(frappe.user_roles || []);
		const can_publish = roles.has("Counselor") || roles.has("Academic Admin") || roles.has("System Manager");

		if (!frm.is_new() && can_publish) {
			// Publish / Republish
			const label = (st === "Published") ? __("Republish") : __("Publish");
			const pub_btn = frm.add_custom_button(label, () => open_publish_dialog(frm));
			pub_btn.removeClass("btn-default").addClass("btn-primary");
			pub_btn.find("span").prepend(frappe.utils.icon("send", "sm"));

			// Open Acknowledgements (filter ToDos for this SSG)
			const ack_btn = frm.add_custom_button(__("Acknowledgements"), () => {
				frappe.set_route("List", "ToDo", {
					reference_type: "Student Support Guidance",
					reference_name: frm.doc.name,
					status: "Open"
				});
			});
			ack_btn.removeClass("btn-default").addClass("btn-secondary");
			ack_btn.find("span").prepend(frappe.utils.icon("bell", "sm"));
		}
	}
});

function open_publish_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Publish Guidance"),
		fields: [
			{ fieldname: "notify", fieldtype: "Check", label: __("Notify teachers via email"), default: 1 },
			{ fieldname: "info", fieldtype: "HTML" }
		],
		primary_action_label: __("Publish"),
		primary_action: async (v) => {
			d.disable_primary_action();
			try {
				await frappe.call({
					method: "ifitwala_ed.students.doctype.student_support_guidance.student_support_guidance.publish",
					args: { name: frm.doc.name, notify: v.notify ? 1 : 0 },
					freeze: true,
					freeze_message: __("Publishing…")
				});
				frappe.show_alert({ message: __("Published"), indicator: "green" });
				await frm.reload_doc();
			} finally {
				d.hide();
			}
		}
	});

	// Small explainer to set expectations
	const hp = cint(frm.doc.high_priority_count || 0);
	const ackn = cint(frm.doc.ack_required_count || 0);
	const msg = `
		<div class="text-muted small">
			<p>${__("Publishing will:")}</p>
			<ul class="ps-3 mb-2">
				<li>${__("Update the teacher snapshot")}</li>
				<li>${__("Bump the acknowledgement version and (re)assign ToDos to current teachers-of-record")}</li>
			</ul>
			<p class="mb-0">${__("Summary")}:
				<strong>${__("High-priority items")}:</strong> ${hp} ·
				<strong>${__("Require ack")}:</strong> ${ackn}
			</p>
		</div>`;
	d.get_field("info").$wrapper.html(msg);

	d.show();
}

// tiny helper mirroring server’s cint
function cint(v) {
	const n = parseInt(v, 10);
	return isNaN(n) ? 0 : n;
}
