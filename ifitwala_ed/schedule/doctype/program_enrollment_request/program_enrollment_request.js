function setAcademicYearQuery(frm) {
	frm.set_query("academic_year", () => {
		const query = { filters: {}, order_by: "year_start_date desc" };
		if (Array.isArray(frm._offeringAcademicYears) && frm._offeringAcademicYears.length) {
			query.filters.name = ["in", frm._offeringAcademicYears];
		}
		return query;
	});
}

async function loadOfferingAcademicYears(frm) {
	if (!frm.doc.program_offering) {
		frm._offeringAcademicYears = [];
		return [];
	}

	const response = await frappe.call({
		method: "ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment.get_offering_ay_spine",
		args: { offering: frm.doc.program_offering },
	});
	const rows = response.message || [];
	frm._offeringAcademicYears = rows
		.map((row) => row.academic_year)
		.filter((academicYear) => Boolean(academicYear));
	return frm._offeringAcademicYears;
}

async function syncAcademicYearState(frm) {
	const ayNames = await loadOfferingAcademicYears(frm);
	const hasOffering = Boolean(frm.doc.program_offering);
	const shouldLock = hasOffering && ayNames.length === 1;

	frm.set_df_property("academic_year", "read_only", shouldLock ? 1 : 0);

	if (!hasOffering) {
		if (frm.doc.academic_year) {
			await frm.set_value("academic_year", null);
		}
		return;
	}

	if (frm.doc.academic_year && !ayNames.includes(frm.doc.academic_year)) {
		await frm.set_value("academic_year", null);
		frappe.show_alert({
			message: __("Academic Year was cleared because it is not part of the selected Program Offering."),
			indicator: "orange",
		});
	}

	if (!frm.doc.academic_year && ayNames.length === 1) {
		await frm.set_value("academic_year", ayNames[0]);
	}

	frm.refresh_field("academic_year");
}

function hasValue(value) {
	return Boolean(String(value || "").trim());
}

function isSystemManager() {
	return Boolean(
		(frappe.user && frappe.user.has_role && frappe.user.has_role("System Manager")) ||
			(frappe.user_roles || []).includes("System Manager")
	);
}

function applyEducatorReviewCopy(frm) {
	frm.set_df_property("request_kind", "label", __("Request Type"));
	frm.set_df_property("status", "label", __("Review Status"));
	frm.set_df_property("section_break_courses", "label", __("Course Choices"));
	frm.set_df_property("courses", "label", __("Selected Courses"));
	frm.set_df_property("section_break_validation", "label", __("Review Summary"));
	frm.set_df_property("validation_status", "label", __("Review Result"));
	frm.set_df_property("validation_payload", "label", __("Technical Validation Log"));
	frm.set_df_property("validation_payload", "description", __("Technical troubleshooting detail."));
	frm.set_df_property("requires_override", "label", __("Needs School Override"));
	frm.set_df_property("override_approved", "label", __("School Override Approved"));
	frm.set_df_property("override_reason", "label", __("Override Notes"));
	frm.set_df_property("section_break_audit", "label", __("Request History"));
}

function toggleRequestTypeFields(frm) {
	const requestKind = String(frm.doc.request_kind || "Academic").trim() || "Academic";
	frm.toggle_display("activity_booking", requestKind === "Activity");
}

function toggleTechnicalReviewFields(frm) {
	const systemManager = isSystemManager();
	const showValidationMeta =
		systemManager ||
		String(frm.doc.validation_status || "").trim() !== "Not Validated" ||
		hasValue(frm.doc.validated_on) ||
		hasValue(frm.doc.validated_by);
	const showOverrideFields =
		systemManager ||
		Boolean(
			Number(frm.doc.requires_override || 0) === 1 ||
				Number(frm.doc.override_approved || 0) === 1 ||
				hasValue(frm.doc.override_reason) ||
				hasValue(frm.doc.override_by) ||
				hasValue(frm.doc.override_on)
		);
	const showHistoryFields =
		systemManager ||
		hasValue(frm.doc.selection_window) ||
		hasValue(frm.doc.source_student_applicant) ||
		hasValue(frm.doc.source_applicant_enrollment_plan) ||
		hasValue(frm.doc.submitted_on) ||
		hasValue(frm.doc.submitted_by);

	frm.toggle_display("validation_payload", systemManager);
	frm.toggle_display(["validated_on", "validated_by"], showValidationMeta);
	frm.toggle_display(
		["requires_override", "override_approved", "override_reason", "override_by", "override_on"],
		showOverrideFields
	);
	frm.toggle_display(
		["selection_window", "source_student_applicant", "source_applicant_enrollment_plan", "submitted_on", "submitted_by"],
		showHistoryFields
	);
}

frappe.ui.form.on("Program Enrollment Request", {
	refresh(frm) {
		setAcademicYearQuery(frm);
		applyEducatorReviewCopy(frm);
		syncAcademicYearState(frm);
		toggleRequestTypeFields(frm);
		toggleTechnicalReviewFields(frm);
	},

	program_offering(frm) {
		syncAcademicYearState(frm);
	},

	request_kind(frm) {
		toggleRequestTypeFields(frm);
	},

	status(frm) {
		toggleTechnicalReviewFields(frm);
	},

	validation_status(frm) {
		toggleTechnicalReviewFields(frm);
	},
});
