// ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.js

frappe.ui.form.on("Applicant Enrollment Plan", {
	refresh(frm) {
		if (!frm.doc || frm.is_new()) {
			return;
		}

		frm.remove_custom_button(__("Mark Ready for Committee"), __("Actions"));
		frm.remove_custom_button(__("Approve Committee"), __("Actions"));
		frm.remove_custom_button(__("Send Offer"), __("Actions"));
		frm.remove_custom_button(__("Hydrate Enrollment Request"), __("Actions"));
		frm.remove_custom_button(__("Open Enrollment Request"), __("Actions"));

		const status = String(frm.doc.status || "").trim();
		if (status === "Draft") {
			frm.add_custom_button(__("Mark Ready for Committee"), () => {
				frm.call("mark_ready_for_committee").then(() => frm.reload_doc());
			}, __("Actions"));
		}

		if (status === "Ready for Committee") {
			frm.add_custom_button(__("Approve Committee"), () => {
				frm.call("approve_committee").then(() => frm.reload_doc());
			}, __("Actions"));
		}

		if (status === "Committee Approved") {
			frm.add_custom_button(__("Send Offer"), () => {
				frm.call("send_offer").then(() => frm.reload_doc());
			}, __("Actions"));
		}

		if (status === "Offer Accepted") {
			frm.add_custom_button(__("Hydrate Enrollment Request"), () => {
				frm.call("hydrate_program_enrollment_request").then((res) => {
					const requestName = res?.message?.name;
					if (requestName) {
						frappe.set_route("Form", "Program Enrollment Request", requestName);
					} else {
						frm.reload_doc();
					}
				});
			}, __("Actions"));
		}

		if (frm.doc.program_enrollment_request) {
			frm.add_custom_button(__("Open Enrollment Request"), () => {
				frappe.set_route("Form", "Program Enrollment Request", frm.doc.program_enrollment_request);
			}, __("Actions"));
		}
	},
});
