// Copyright (c) 2026, Francois de Ryckel and contributors
// For license information, please see license.txt

const VIEW_MODE_MATRIX = "Student x Course Matrix";
const VIEW_MODE_WINDOW_TRACKER = "Selection Window Tracker";
const FAST_TRACK_BUTTON_KEY = "per-fast-track-btn";
const FAST_TRACK_PROGRESS_EVENT = "program_enrollment_request_fast_track";
const FAST_TRACK_DONE_EVENT = "program_enrollment_request_fast_track_done";

async function refreshSchoolScope(report) {
	const school = report.get_filter_value("school") || "";
	if (!school) {
		frappe.query_report.__school_scope = [];
		return;
	}

	const response = await frappe.call({
		method: "ifitwala_ed.utilities.school_tree.get_descendant_schools",
		args: { user_school: school }
	});

	frappe.query_report.__school_scope = response.message || [school];
	const programOfferingFilter = report.get_filter("program_offering");
	if (programOfferingFilter) {
		programOfferingFilter.refresh();
	}
}

function getIndicatorColor(value, mapping, fallback = "gray") {
	return mapping[String(value || "").trim()] || fallback;
}

function syncViewModeFilters(report) {
	if (!report) {
		return;
	}

	const viewMode = report.get_filter_value("view_mode");
	const programOffering = report.get_filter("program_offering");
	if (programOffering) {
		programOffering.df.reqd = viewMode === VIEW_MODE_MATRIX ? 1 : 0;
		programOffering.refresh();
	}

	const selectionWindow = report.get_filter("selection_window");
	if (selectionWindow) {
		selectionWindow.df.reqd = viewMode === VIEW_MODE_WINDOW_TRACKER ? 1 : 0;
		selectionWindow.refresh();
	}
}

function prettyCountLabel(key) {
	return String(key || "")
		.split("_")
		.map((part) => part.charAt(0).toUpperCase() + part.slice(1))
		.join(" ");
}

function buildFastTrackMessage(summary) {
	const counts = Object.entries(summary?.counts || {})
		.map(([key, value]) => `${frappe.utils.escape_html(prettyCountLabel(key))}: ${value}`)
		.join("<br>");
	const detailsLink = summary?.details_link
		? `<br><br><a href="${summary.details_link}" target="_blank" rel="noopener noreferrer">${__("Download details CSV")}</a>`
		: "";
	return `${counts}${detailsLink}`;
}

function canShowFastTrackButton() {
	return Boolean(frappe.query_report.__fastTrackAccess?.can_run);
}

function ensureFastTrackRealtimeBinding() {
	if (frappe.query_report.__fastTrackRealtimeBound) {
		return;
	}

	frappe.realtime.on(FAST_TRACK_PROGRESS_EVENT, (data) => {
		frappe.hide_msgprint(true);
		frappe.show_progress(
			data?.action_label || __("Approving and creating enrollments"),
			data?.progress?.[0] || 0,
			data?.progress?.[1] || 0
		);
	});

	frappe.realtime.on(FAST_TRACK_DONE_EVENT, (summary) => {
		frappe.hide_msgprint(true);
		frappe.msgprint({
			title: summary?.title || __("Fast-Track Enrollment Finished"),
			message: buildFastTrackMessage(summary),
			indicator: "green"
		});
		if (frappe.query_report) {
			frappe.query_report.refresh();
		}
	});

	frappe.query_report.__fastTrackRealtimeBound = true;
}

function getCurrentReportFilters() {
	const report = frappe.query_report;
	return Object.assign({}, report?.get_values?.() || {});
}

function validateFastTrackFilters(filters) {
	if (String(filters?.latest_request_only || 0) !== "1") {
		frappe.msgprint(
			__("Fast-track enrollment requires Latest Request Only so older requests cannot materialize over newer intent.")
		);
		return false;
	}

	const requestKind = String(filters?.request_kind || "Academic").trim() || "Academic";
	if (requestKind !== "Academic") {
		frappe.msgprint(__("Fast-track enrollment only supports Academic requests."));
		return false;
	}

	return true;
}

function renderFastTrackPreview(preview) {
	const counts = preview?.counts || {};
	const rows = [
		[__("Selected"), counts.selected || 0],
		[__("Currently Valid"), counts.currently_valid || 0],
		[__("Ready Now"), counts.ready_now || 0],
		[__("Pending Validation"), counts.pending_validation || 0],
		[__("Currently Invalid"), counts.currently_invalid || 0],
		[__("Needs Override"), counts.needs_override || 0],
		[__("Already Materialized"), counts.already_materialized || 0],
		[__("Terminal"), counts.terminal || 0]
	];

	const body = rows
		.map(
			([label, value]) =>
				`<div style="display:flex;justify-content:space-between;padding:4px 0;"><span>${frappe.utils.escape_html(label)}</span><strong>${value}</strong></div>`
		)
		.join("");

	return `
		<div class="mb-3">
			<p class="text-muted">${frappe.utils.escape_html(preview?.note || "")}</p>
		</div>
		<div>${body}</div>
	`;
}

async function handleFastTrackRun(dialog, filters) {
	const values = dialog.get_values() || {};
	const response = await frappe.call({
		method: "ifitwala_ed.schedule.program_enrollment_request_fast_track.run_fast_track_requests",
		args: {
			filters: JSON.stringify(filters),
			enrollment_date: values.enrollment_date || ""
		},
		freeze: true,
		freeze_message: __("Fast-tracking clean requests...")
	});

	dialog.hide();
	const summary = response?.message || {};
	if (summary.queued) {
		frappe.msgprint({
			title: __("Fast-Track Queued"),
			message: summary.message || __("The selected requests were queued for fast-track processing."),
			indicator: "blue"
		});
		return;
	}

	frappe.msgprint({
		title: summary?.title || __("Fast-Track Enrollment Finished"),
		message: buildFastTrackMessage(summary),
		indicator: "green"
	});
	if (frappe.query_report) {
		frappe.query_report.refresh();
	}
}

async function openFastTrackDialog() {
	const filters = getCurrentReportFilters();
	if (!validateFastTrackFilters(filters)) {
		return;
	}

	const response = await frappe.call({
		method: "ifitwala_ed.schedule.program_enrollment_request_fast_track.preview_fast_track_requests",
		args: { filters: JSON.stringify(filters) },
		freeze: true,
		freeze_message: __("Checking clean requests...")
	});
	const preview = response?.message || {};

	const dialog = new frappe.ui.Dialog({
		title: __("Approve + Create Enrollments"),
		fields: [
			{
				fieldname: "preview_html",
				fieldtype: "HTML"
			},
			{
				fieldname: "enrollment_date",
				fieldtype: "Date",
				label: __("Enrollment Date"),
				default: preview.default_enrollment_date || "",
				description: __("Defaults to the Academic Year start date when left blank.")
			}
		],
		primary_action_label: __("Approve + Create Enrollments"),
		primary_action: async () => {
			await handleFastTrackRun(dialog, filters);
		}
	});

	dialog.fields_dict.preview_html.$wrapper.html(renderFastTrackPreview(preview));
	dialog.show();
}

function ensureFastTrackButton(page) {
	if (!page?.add_inner_button) return;
	const existingButton =
		page.inner_toolbar && page.inner_toolbar.find(`button[data-key="${FAST_TRACK_BUTTON_KEY}"]`);

	if (!canShowFastTrackButton()) {
		existingButton?.remove();
		return;
	}

	if (existingButton?.length) {
		return;
	}

	const button = page.add_inner_button(__("Approve + Create Enrollments"), () => {
		openFastTrackDialog().catch((error) => {
			frappe.msgprint(error?.message || __("Unable to start fast-track enrollment."));
		});
	});
	if (button) {
		button.attr("data-key", FAST_TRACK_BUTTON_KEY);
		button.removeClass("btn-default").addClass("btn-primary btn-sm");
	}
}

frappe.query_reports["Program Enrollment Request Overview"] = {
	filters: [
		{
			fieldname: "view_mode",
			label: __("View"),
			fieldtype: "Select",
			options: `${VIEW_MODE_MATRIX}\nCourse Demand Summary\n${VIEW_MODE_WINDOW_TRACKER}`,
			default: VIEW_MODE_MATRIX,
			reqd: 1,
			on_change() {
				syncViewModeFilters(frappe.query_report);
			}
		},
		{
			fieldname: "school",
			label: __("School"),
			fieldtype: "Link",
			options: "School",
			reqd: 1,
			get_query() {
				return {
					filters: {
						name: ["in", frappe.query_report.__allowed_schools || []]
					}
				};
			},
			async on_change() {
				const report = frappe.query_report;
				const programOffering = report.get_filter("program_offering");
				if (programOffering) {
					programOffering.set_value("");
				}
				await refreshSchoolScope(report);
			}
		},
		{
			fieldname: "academic_year",
			label: __("Academic Year"),
			fieldtype: "Link",
			options: "Academic Year",
			reqd: 1,
			get_query() {
				const school = frappe.query_report.get_filter_value("school") || "";
				return {
					query: "ifitwala_ed.schedule.report.enrollment_gaps_report.enrollment_gaps_report.academic_year_link_query",
					filters: { school }
				};
			}
		},
		{
			fieldname: "program",
			label: __("Program"),
			fieldtype: "Link",
			options: "Program",
			on_change() {
				const programOffering = frappe.query_report.get_filter("program_offering");
				if (programOffering) {
					programOffering.set_value("");
				}
			}
		},
		{
			fieldname: "program_offering",
			label: __("Program Offering"),
			fieldtype: "Link",
			options: "Program Offering",
			get_query() {
				const filters = {};
				const program = frappe.query_report.get_filter_value("program");
				const schoolScope = frappe.query_report.__school_scope || [];
				if (program) {
					filters.program = program;
				}
				if (schoolScope.length) {
					filters.school = ["in", schoolScope];
				}
				return { filters };
			}
		},
		{
			fieldname: "selection_window",
			label: __("Selection Window"),
			fieldtype: "Link",
			options: "Program Offering Selection Window",
			get_query() {
				const filters = {};
				const schoolScope = frappe.query_report.__school_scope || [];
				const academicYear = frappe.query_report.get_filter_value("academic_year");
				const programOffering = frappe.query_report.get_filter_value("program_offering");
				if (schoolScope.length) {
					filters.school = ["in", schoolScope];
				}
				if (academicYear) {
					filters.academic_year = academicYear;
				}
				if (programOffering) {
					filters.program_offering = programOffering;
				}
				return { filters };
			}
		},
		{
			fieldname: "request_kind",
			label: __("Request Kind"),
			fieldtype: "Select",
			options: "\nAcademic\nActivity",
			default: "Academic"
		},
		{
			fieldname: "request_status",
			label: __("Request Status"),
			fieldtype: "Select",
			options: "\nDraft\nSubmitted\nUnder Review\nApproved\nRejected\nCancelled"
		},
		{
			fieldname: "validation_status",
			label: __("Validation"),
			fieldtype: "Select",
			options: "\nNot Validated\nValid\nInvalid"
		},
		{
			fieldname: "requires_override",
			label: __("Needs Override"),
			fieldtype: "Check"
		},
		{
			fieldname: "invalid_reason_bucket",
			label: __("Invalid Reason"),
			fieldtype: "Select",
			options:
				"\nPrerequisite\nCapacity Full\nBasket Missing Required\nBasket Group Not Selected\nBasket Group Coverage\nRepeat / Max Attempts\nCourse Not In Offering\nRule Misconfigured / Unsupported\nOther"
		},
		{
			fieldname: "latest_request_only",
			label: __("Latest Request Only"),
			fieldtype: "Check",
			default: 1
		}
	],

	async onload(report) {
		report.page.set_title(__("Program Enrollment Request Overview"));
		ensureFastTrackRealtimeBinding();

		const [allowedSchoolResponse, fastTrackAccessResponse] = await Promise.all([
			frappe.call({
				method: "ifitwala_ed.school_settings.school_settings_utils.get_user_allowed_schools"
			}),
			frappe.call({
				method: "ifitwala_ed.schedule.program_enrollment_request_fast_track.get_fast_track_access"
			})
		]);
		const allowedSchools = allowedSchoolResponse.message || [];
		frappe.query_report.__fastTrackAccess = fastTrackAccessResponse.message || { can_run: 0 };
		frappe.query_report.__allowed_schools = allowedSchools;
		ensureFastTrackButton(report.page);

		if (!allowedSchools.length) {
			frappe.msgprint(__("You do not have a default school assigned. Please contact your administrator."));
			return;
		}

		const schoolFilter = report.get_filter("school");
		if (schoolFilter && !schoolFilter.get_value()) {
			schoolFilter.set_value(allowedSchools[0]);
		}
		if (schoolFilter) {
			schoolFilter.df.read_only = allowedSchools.length === 1 ? 1 : 0;
			schoolFilter.refresh();
		}

		await refreshSchoolScope(report);
		syncViewModeFilters(report);
	},

	after_datatable_render(report) {
		if (report?.page) {
			ensureFastTrackButton(report.page);
		}
	},

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "request_status" && data) {
			const color = getIndicatorColor(data.request_status, {
				Draft: "gray",
				Submitted: "blue",
				"Under Review": "orange",
				Approved: "green",
				Rejected: "red",
				Cancelled: "darkgrey"
			});
			return `<span class="indicator-pill ${color}">${frappe.utils.escape_html(data.request_status || "")}</span>`;
		}

		if (column.fieldname === "validation_status" && data) {
			const color = getIndicatorColor(data.validation_status, {
				"Not Validated": "gray",
				Valid: "green",
				Invalid: "red"
			});
			return `<span class="indicator-pill ${color}">${frappe.utils.escape_html(data.validation_status || "")}</span>`;
		}

		if (column.fieldname === "submission_status" && data) {
			const color = getIndicatorColor(data.submission_status, {
				Submitted: "green",
				"Not Submitted": "orange",
				"Missing Request": "red"
			});
			return `<span class="indicator-pill ${color}">${frappe.utils.escape_html(data.submission_status || "")}</span>`;
		}

		if (column.fieldname === "current_state" && data) {
			const color = getIndicatorColor(data.current_state, {
				"Ready to Submit": "green",
				Blocked: "orange",
				Valid: "green",
				Invalid: "red",
				"Not Validated": "gray",
				"Missing Request": "red"
			});
			return `<span class="indicator-pill ${color}">${frappe.utils.escape_html(data.current_state || "")}</span>`;
		}

		if (column.fieldname === "problem_status" && data) {
			const text = String(data.problem_status || "").trim();
			if (!text) {
				return "";
			}
			const color = getIndicatorColor(text, {
				"Selection Blocked": "orange",
				"Invalid Request": "red",
				"Needs Override": "orange",
				"Missing Request": "red"
			});
			return `<span class="indicator-pill ${color}">${frappe.utils.escape_html(text)}</span>`;
		}

		if (column.fieldname.startsWith("course_")) {
			const text = String(data?.[column.fieldname] || "").trim();
			if (!text) {
				return "";
			}
			const color =
				text === "Required" ? "green" :
				text === "Selected" ? "blue" :
				text.startsWith("Choice") ? "orange" :
				text === "Approved" ? "green" :
				text === "Waitlisted" ? "orange" :
				text === "Rejected" ? "red" :
				"blue";
			return `<div class="text-center"><span class="indicator-pill ${color}">${frappe.utils.escape_html(text)}</span></div>`;
		}

		if (column.fieldtype === "Int" && value !== undefined && value !== null && value !== "") {
			return `<div class="text-end">${value}</div>`;
		}

		return value;
	},

	get_datatable_options(options) {
		const viewMode = frappe.query_report.get_filter_value("view_mode");
		return Object.assign(options, {
			checkboxColumn: false,
			freezeColumn: viewMode === VIEW_MODE_MATRIX ? 5 : viewMode === VIEW_MODE_WINDOW_TRACKER ? 4 : 2,
			noDataMessage:
				viewMode === VIEW_MODE_MATRIX
					? __("No enrollment requests match these filters.")
					: viewMode === VIEW_MODE_WINDOW_TRACKER
						? __("No selection-window responses match these filters.")
						: __("No course demand matches these filters.")
		});
	}
};
