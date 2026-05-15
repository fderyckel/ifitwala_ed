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

const VIEW_MODE_MATRIX = "Student x Course Matrix";
const VIEW_MODE_WINDOW_TRACKER = "Selection Window Tracker";

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

function safeParseValidationPayload(value) {
	if (!hasValue(value)) return null;
	try {
		return JSON.parse(value);
	} catch (error) {
		return null;
	}
}

function extractBasketGroupName(message) {
	const text = String(message || "").trim();
	const match = text.match(/'([^']+)'/);
	return match ? String(match[1] || "").trim() : "";
}

function formatEducatorBasketMessage(entry) {
	const payload = typeof entry === "string" ? { message: entry } : (entry || {});
	const code = String(payload.code || "").trim();
	const message = String(payload.message || "").trim();

	if (code === "missing_required" || message === "Missing required courses in basket.") {
		return __("A required course is missing from this request.");
	}

	if (
		code === "ambiguous_basket_group" ||
		message === "One or more selected courses must be assigned to a basket group before validation can pass."
	) {
		return __("A selected course still needs a choice section before the request can advance.");
	}

	if (code === "require_group_coverage" || message.startsWith("Basket must include at least one course from group")) {
		const groupName = extractBasketGroupName(message);
		return groupName
			? __("Choice section still missing: {0}.", [groupName])
			: __("A required choice section is still missing.");
	}

	return message || null;
}

function formatEducatorCourseReason(courseLabel, reason) {
	const text = String(reason || "").trim();
	if (!text) return null;

	if (text === "Capacity full for this course.") {
		return null;
	}

	if (text === "Course is not part of the Program Offering.") {
		return __("{0} is no longer part of this program offering.", [courseLabel]);
	}

	if (
		text === "Prerequisite requirements not met." ||
		text === "Rule not supported by current schema." ||
		(text.startsWith("Required course ") && text.endsWith(" not completed.")) ||
		text.startsWith("No numeric score evidence for ") ||
		(text.startsWith("Required ") && text.includes(" score ") && text.includes("; got "))
	) {
		return __("{0} needs prerequisite review before the request can advance.", [courseLabel]);
	}

	if (text === "Course already completed and not repeatable.") {
		return __("{0} has already been completed and cannot be selected again.", [courseLabel]);
	}

	if (text === "Maximum attempts exceeded.") {
		return __("{0} has already reached the maximum number of attempts.", [courseLabel]);
	}

	return courseLabel ? __("{0}: {1}", [courseLabel, text]) : text;
}

function buildEducatorReviewMessages(frm) {
	const validationStatus = String(frm.doc.validation_status || "").trim();
	const requestStatus = String(frm.doc.status || "").trim();
	const payload = safeParseValidationPayload(frm.doc.validation_payload);
	const messages = [];
	const seen = new Set();

	function push(message) {
		const normalized = String(message || "").trim();
		if (!normalized || seen.has(normalized)) return;
		seen.add(normalized);
		messages.push(normalized);
	}

	if (validationStatus === "Invalid") {
		if (Number(frm.doc.requires_override || 0) === 1) {
			push(__("School override is required before this request can be approved."));
		}

		const basket = payload?.results?.basket || {};
		if (payload?.summary?.basket_not_configured || basket.status === "not_configured") {
			push(__("Program Offering has no enrollment rules. Add at least one rule before this request can validate."));
		}
		for (const violation of basket.violations || []) {
			push(formatEducatorBasketMessage(violation));
		}
		for (const reason of basket.reasons || []) {
			push(formatEducatorBasketMessage(reason));
		}

		const capacityCourses = [];
		for (const row of payload?.results?.courses || []) {
			if (!row?.blocked) continue;
			const courseLabel = String(row.course || "").trim();
			const reasons = Array.from(
				new Set((row.reasons || []).map((reason) => String(reason || "").trim()).filter(Boolean))
			);

			if (reasons.includes("Capacity full for this course.") && courseLabel) {
				capacityCourses.push(courseLabel);
			}

			for (const reason of reasons) {
				push(formatEducatorCourseReason(courseLabel, reason));
			}
		}

		if (capacityCourses.length === 1) {
			push(__("No places are currently available in {0}.", [capacityCourses[0]]));
		} else if (capacityCourses.length > 1) {
			push(__("No places are currently available in: {0}.", [capacityCourses.join(", ")]));
		}

		if (!messages.length) {
			push(__("This request still needs review before it can advance."));
		}
	}

	if (!messages.length && validationStatus === "Valid" && ["Submitted", "Under Review", "Approved"].includes(requestStatus)) {
		push(__("Validation checks are complete and this request is ready for academic review."));
	}

	return messages;
}

function renderEducatorReviewBanner(frm) {
	if (!frm.dashboard || !frm.dashboard.set_headline) return;

	const messages = buildEducatorReviewMessages(frm);
	if (!messages.length) {
		frm.dashboard.set_headline("");
		return;
	}

	const validationStatus = String(frm.doc.validation_status || "").trim();
	const toneClass = validationStatus === "Invalid" ? "text-danger" : "text-success";
	const html = messages.map((message) => `• ${frappe.utils.escape_html(message)}`).join("<br>");
	frm.dashboard.set_headline(`<span class="${toneClass}">${html}</span>`);
}

function openRequestOverview(frm) {
	if (frm.is_new() || !frm.doc.name) {
		frappe.msgprint(__("Please save this request first."));
		return;
	}

	const routeOptions = {
		school: frm.doc.school || "",
		academic_year: frm.doc.academic_year || "",
		program: frm.doc.program || "",
		program_offering: frm.doc.program_offering || "",
		request_kind: frm.doc.request_kind || "Academic",
		latest_request_only: 1,
	};

	if (hasValue(frm.doc.selection_window)) {
		routeOptions.view_mode = VIEW_MODE_WINDOW_TRACKER;
		routeOptions.selection_window = frm.doc.selection_window;
	} else {
		routeOptions.view_mode = VIEW_MODE_MATRIX;
	}

	frappe.route_options = routeOptions;
	frappe.set_route("query-report", "Program Enrollment Request Overview");
}

frappe.ui.form.on("Program Enrollment Request", {
	refresh(frm) {
		setAcademicYearQuery(frm);
		applyEducatorReviewCopy(frm);
		syncAcademicYearState(frm);
		toggleRequestTypeFields(frm);
		toggleTechnicalReviewFields(frm);
		renderEducatorReviewBanner(frm);

		frm.clear_custom_buttons();
		if (!frm.is_new() && hasValue(frm.doc.program_offering) && hasValue(frm.doc.academic_year) && hasValue(frm.doc.school)) {
			frm.add_custom_button(__("Open Request Overview"), () => openRequestOverview(frm));
		}
	},

	program_offering(frm) {
		syncAcademicYearState(frm);
	},

	request_kind(frm) {
		toggleRequestTypeFields(frm);
	},

	status(frm) {
		toggleTechnicalReviewFields(frm);
		renderEducatorReviewBanner(frm);
	},

	validation_status(frm) {
		toggleTechnicalReviewFields(frm);
		renderEducatorReviewBanner(frm);
	},
});
