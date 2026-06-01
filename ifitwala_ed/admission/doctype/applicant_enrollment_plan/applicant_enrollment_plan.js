// ifitwala_ed/admission/doctype/applicant_enrollment_plan/applicant_enrollment_plan.js

function sync_applicant_full_name(frm) {
	if (!frm.doc.student_applicant) {
		frm.set_value("applicant_full_name", "");
		return;
	}

	frappe.db
		.get_value("Student Applicant", frm.doc.student_applicant, ["first_name", "middle_name", "last_name"])
		.then((res) => {
			const applicant = res?.message || {};
			const fullName = [applicant.first_name, applicant.middle_name, applicant.last_name]
				.map((part) => String(part || "").trim())
				.filter(Boolean)
				.join(" ");

			if (frm.doc.applicant_full_name !== fullName) {
				frm.set_value("applicant_full_name", fullName);
			}
		});
}

function bind_program_offering_course_query(frm) {
	frm.set_query("course", "courses", () => ({
		query:
			"ifitwala_ed.admission.doctype.applicant_enrollment_plan.applicant_enrollment_plan.program_offering_course_link_query",
		filters: {
			program_offering: frm.doc.program_offering || "",
		},
	}));
}

function add_refresh_course_defaults_button(frm, status) {
	if (!["Draft", "Ready for Committee"].includes(status)) {
		return;
	}

	frm.add_custom_button(__("Refresh Course Defaults"), () => {
		if (!frm.doc.program_offering) {
			frappe.msgprint({
				message: __("Choose a Program Offering before refreshing course defaults."),
				indicator: "orange",
			});
			return;
		}

		frm.call("refresh_offering_course_defaults").then((res) => {
			const addedCount = Number(res?.message?.added_courses?.length || 0);
			const message = addedCount
				? __("{0} required course default(s) refreshed.", [addedCount])
				: __("Required course defaults are already up to date.");
			frappe.show_alert({ message, indicator: "green" });
			frm.reload_doc();
		});
	}, __("Actions"));
}

frappe.ui.form.on("Applicant Enrollment Plan", {
	setup(frm) {
		bind_program_offering_course_query(frm);
	},

	refresh(frm) {
		if (!frm.doc) {
			return;
		}

		bind_program_offering_course_query(frm);

		if (frm.doc.student_applicant && !frm.doc.applicant_full_name) {
			sync_applicant_full_name(frm);
		}

		if (frm.is_new()) {
			return;
		}

		frm.remove_custom_button(__("Mark Ready for Committee"), __("Actions"));
		frm.remove_custom_button(__("Approve Committee"), __("Actions"));
		frm.remove_custom_button(__("Send Offer"), __("Actions"));
		frm.remove_custom_button(__("Hydrate Enrollment Request"), __("Actions"));
		frm.remove_custom_button(__("Open Enrollment Request"), __("Actions"));
		frm.remove_custom_button(__("Approve Academic Deposit Override"), __("Actions"));
		frm.remove_custom_button(__("Approve Finance Deposit Override"), __("Actions"));
		frm.remove_custom_button(__("Generate Deposit Invoice"), __("Actions"));
		frm.remove_custom_button(__("Open Deposit Invoice"), __("Actions"));
		frm.remove_custom_button(__("Refresh Course Defaults"), __("Actions"));

		const status = String(frm.doc.status || "").trim();
		const depositRequired = Number(frm.doc.deposit_required || 0) === 1;
		const depositOverrideStatus = String(frm.doc.deposit_override_status || "").trim();
		const depositTermsSource = String(frm.doc.deposit_terms_source || "").trim();

		add_refresh_course_defaults_button(frm, status);

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

		if (depositRequired && depositTermsSource === "Manual Override" && depositOverrideStatus === "Pending") {
			frm.add_custom_button(__("Approve Academic Deposit Override"), () => {
				frm.call("approve_deposit_academic_override").then(() => frm.reload_doc());
			}, __("Actions"));
			frm.add_custom_button(__("Approve Finance Deposit Override"), () => {
				frm.call("approve_deposit_finance_override").then(() => frm.reload_doc());
			}, __("Actions"));
		}

		if (status === "Offer Accepted") {
			if (
				depositRequired &&
				!frm.doc.deposit_invoice &&
				(depositTermsSource !== "Manual Override" || depositOverrideStatus === "Approved")
			) {
				frm.add_custom_button(__("Generate Deposit Invoice"), () => {
					frm.call("generate_deposit_invoice").then(() => frm.reload_doc());
				}, __("Actions"));
			}

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

		if (frm.doc.deposit_invoice) {
			frm.add_custom_button(__("Open Deposit Invoice"), () => {
				frappe.set_route("Form", "Sales Invoice", frm.doc.deposit_invoice);
			}, __("Actions"));
		}

		if (frm.doc.program_enrollment_request) {
			frm.add_custom_button(__("Open Enrollment Request"), () => {
				frappe.set_route("Form", "Program Enrollment Request", frm.doc.program_enrollment_request);
			}, __("Actions"));
		}
	},

	student_applicant(frm) {
		sync_applicant_full_name(frm);
	},

	program_offering(frm) {
		bind_program_offering_course_query(frm);
		frm.refresh_field("courses");
	},
});
