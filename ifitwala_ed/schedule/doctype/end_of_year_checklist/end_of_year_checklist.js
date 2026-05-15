// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.js

const STATUS_COMPLETED = "Completed";

frappe.ui.form.on("End of Year Checklist", {
	refresh(frm) {
		applyAcademicYearRouteContext(frm);
		ensure_defaults(frm);
		set_scope_queries(frm);
		refresh_scope_preview(frm);
		refresh_curriculum_preview(frm);
		apply_status_rules(frm);
	},
	school(frm) {
		frm.set_value("academic_year", null);
		frm.set_value("curriculum_target_academic_year", null);
		refresh_scope_preview(frm, { clear_on_error: true });
		refresh_curriculum_preview(frm);
	},
	academic_year(frm) {
		refresh_curriculum_preview(frm);
	},
	curriculum_target_academic_year(frm) {
		refresh_curriculum_preview(frm);
	},
	status(frm) {
		apply_status_rules(frm);
	},
	prepare_curriculum_handover(frm) {
		run_curriculum_handover(frm);
	},
	archive_terms(frm) {
		run_action(frm, "archive_terms", __("Terms archived."));
	},
	archive_program_enrollment(frm) {
		run_action(frm, "archive_program_enrollment", __("Program Enrollments archived."));
	},
	archive_student_groups(frm) {
		run_action(frm, "archive_student_groups", __("Student Groups retired."));
	},
	archive_academic_year(frm) {
		run_action(frm, "archive_academic_year", __("Academic Years archived."));
	},
});

function applyAcademicYearRouteContext(frm) {
	const routeOptions = frappe.route_options || {};
	if (!routeOptions.from_academic_year_form) {
		return;
	}

	frappe.route_options = null;

	const updates = {};
	if (routeOptions.school && routeOptions.school !== frm.doc.school) {
		updates.school = routeOptions.school;
	}
	if (routeOptions.academic_year && routeOptions.academic_year !== frm.doc.academic_year) {
		updates.academic_year = routeOptions.academic_year;
	}
	if (!Object.keys(updates).length) {
		return;
	}

	frm.set_value(updates);
}

function ensure_defaults(frm) {
	if (!frm.doc.status) {
		frm.set_value("status", "Draft");
	}
}

function set_scope_queries(frm) {
	frm.set_query("school", () => ({
		query: "ifitwala_ed.schedule.doctype.end_of_year_checklist.end_of_year_checklist.school_link_query",
	}));

	frm.set_query("academic_year", () => {
		if (!frm.doc.school) {
			return {
				filters: { name: "" },
			};
		}
		return {
			query: "ifitwala_ed.schedule.doctype.end_of_year_checklist.end_of_year_checklist.academic_year_link_query",
			filters: { school: frm.doc.school },
		};
	});

	frm.set_query("curriculum_target_academic_year", () => {
		if (!frm.doc.school) {
			return {
				filters: { name: "" },
			};
		}
		return {
			query: "ifitwala_ed.schedule.doctype.end_of_year_checklist.end_of_year_checklist.academic_year_link_query",
			filters: { school: frm.doc.school },
		};
	});
}

function apply_status_rules(frm) {
	const completed = frm.doc.status === STATUS_COMPLETED;
	const scope_ok = frm.__eoy_scope_valid !== false;
	const lock_fields = ["school", "academic_year", "curriculum_target_academic_year", "status"];
	const action_buttons = [
		"prepare_curriculum_handover",
		"archive_program_enrollment",
		"archive_student_groups",
		"archive_terms",
		"archive_academic_year",
	];

	lock_fields.forEach((fieldname) => {
		frm.set_df_property(fieldname, "read_only", completed ? 1 : 0);
	});
	action_buttons.forEach((fieldname) => {
		const locked =
			fieldname === "prepare_curriculum_handover"
				? completed || !scope_ok || !frm.doc.curriculum_target_academic_year
				: completed || !scope_ok;
		frm.set_df_property(fieldname, "read_only", locked ? 1 : 0);
	});
}

function refresh_scope_preview(frm, options = {}) {
	const wrapper = frm.get_field("scope_preview")?.$wrapper;
	if (!wrapper) {
		return;
	}

	if (!frm.doc.school) {
		frm.__eoy_scope_valid = false;
		apply_status_rules(frm);
		wrapper.html(`<div class='text-muted'>${frappe.utils.escape_html(__("Select a school to preview scope."))}</div>`);
		return;
	}

	frappe.call({
		method: "ifitwala_ed.schedule.doctype.end_of_year_checklist.end_of_year_checklist.get_scope_preview",
		args: { school: frm.doc.school },
	})
		.then((res) => {
			const rows = res?.message?.schools || [];
			const count = res?.message?.count || rows.length;
			frm.__eoy_scope_valid = true;
			apply_status_rules(frm);
			if (!rows.length) {
				wrapper.html(`<div class='text-muted'>${frappe.utils.escape_html(__("No schools resolved for the current selection."))}</div>`);
				refresh_curriculum_preview(frm);
				return;
			}
			const list = rows
				.map((row) => frappe.utils.escape_html(row.school_name || row.name))
				.join(", ");
			const header = `<strong>${frappe.utils.escape_html(__("{0} school(s):", [count]))}</strong> `;
			wrapper.html(`<div>${header}${list}</div>`);
			refresh_curriculum_preview(frm);
		})
		.catch((err) => {
			const message = err?.message || __("Unable to resolve school scope.");
			frm.__eoy_scope_valid = false;
			apply_status_rules(frm);
			frappe.msgprint(message);
			wrapper.html(`<div class='text-danger'>${frappe.utils.escape_html(message)}</div>`);
			if (options.clear_on_error) {
				frm.set_value("school", null);
				frm.set_value("academic_year", null);
				frm.set_value("curriculum_target_academic_year", null);
			}
			refresh_curriculum_preview(frm);
		});
}

function ensure_ready_for_action(frm) {
	if (!frm.doc.school || !frm.doc.academic_year) {
		frappe.msgprint(__("Select a School and Academic Year before running this action."));
		return false;
	}
	if (!frm.doc.status || frm.doc.status === "Draft") {
		frappe.msgprint(__("Set status to In Progress before running actions."));
		return false;
	}
	if (frm.doc.status === STATUS_COMPLETED) {
		frappe.msgprint(__("Checklist is completed and actions are locked."));
		return false;
	}
	return true;
}

function run_action(frm, method, successMessage) {
	if (!ensure_ready_for_action(frm)) {
		return;
	}
	frappe.call({
		method: "ifitwala_ed.schedule.doctype.end_of_year_checklist.end_of_year_checklist.get_scope_preview",
		args: { school: frm.doc.school },
	})
		.then((res) => {
			const rows = res?.message?.schools || [];
			const count = res?.message?.count || rows.length;
			const list = rows
				.map((row) => frappe.utils.escape_html(row.school_name || row.name))
				.join(", ");
			const scopeLine = list ? `<br><strong>${frappe.utils.escape_html(__("{0} school(s):", [count]))}</strong> ${list}` : "";
			const message = [
				__("You are about to run an end-of-year action."),
				`<br><strong>${__("Target School")}:</strong> ${frappe.utils.escape_html(frm.doc.school)}`,
				`<br><strong>${__("Academic Year")}:</strong> ${frappe.utils.escape_html(frm.doc.academic_year)}`,
				scopeLine,
				`<br><br><strong>${__("Warning")}:</strong> ${__("This is irreversible.")}`,
			].join("");

			frappe.confirm(message, () => {
				frm.call({ method, freeze: true })
					.then((actionRes) => {
						if (successMessage) {
							frappe.msgprint(successMessage);
						}
						return actionRes;
					})
					.catch((err) => {
						frappe.msgprint(err?.message || __("Unable to run this action."));
					});
			});
		})
		.catch((err) => {
			frappe.msgprint(err?.message || __("Unable to resolve school scope."));
		});
}

function refresh_curriculum_preview(frm) {
	const wrapper = frm.get_field("curriculum_preview")?.$wrapper;
	if (!wrapper) {
		return;
	}

	if (!frm.doc.school || !frm.doc.academic_year) {
		wrapper.html(
			`<div class='text-muted'>${frappe.utils.escape_html(
				__("Select the source School and Academic Year to preview curriculum handover.")
			)}</div>`
		);
		return;
	}

	if (!frm.doc.curriculum_target_academic_year) {
		wrapper.html(
			`<div class='text-muted'>${frappe.utils.escape_html(
				__("Choose the target Academic Year to preview the next-year course plans.")
			)}</div>`
		);
		return;
	}

	frm.call({ method: "get_curriculum_handover_preview" })
		.then((res) => {
			const payload = res?.message || {};
			const summary = payload.summary || {};
			const rows = payload.rows || [];
			const summaryBits = [
				__("Active source plans: {0}", [summary.source_plan_count || 0]),
				__("Ready to create: {0}", [summary.ready_count || 0]),
				__("Already prepared: {0}", [summary.existing_count || 0]),
				__("Missing target year: {0}", [summary.missing_target_academic_year_count || 0]),
				__("No permission: {0}", [summary.no_permission_count || 0]),
			];
			const detailRows = rows
				.slice(0, 8)
				.map((row) => {
					const label = frappe.utils.escape_html(row.title || row.source_course_plan || "");
					const school = frappe.utils.escape_html(row.school || "");
					const status = frappe.utils.escape_html(humanize_curriculum_status(row.status));
					return `<li><strong>${label}</strong>${school ? ` · ${school}` : ""} · ${status}</li>`;
				})
				.join("");
			const details = detailRows ? `<ul class="mt-2">${detailRows}</ul>` : "";
			wrapper.html(`<div><strong>${summaryBits.join(" · ")}</strong>${details}</div>`);
		})
		.catch((err) => {
			wrapper.html(
				`<div class='text-danger'>${frappe.utils.escape_html(
					err?.message || __("Unable to preview curriculum handover.")
				)}</div>`
			);
		});
}

function humanize_curriculum_status(status) {
	const normalized = String(status || "").trim();
	if (normalized === "ready") return __("Ready");
	if (normalized === "existing_target") return __("Already prepared");
	if (normalized === "missing_target_academic_year") return __("Missing target Academic Year");
	if (normalized === "no_permission") return __("No curriculum permission");
	return normalized || __("Unknown");
}

function run_curriculum_handover(frm) {
	if (!frm.doc.school || !frm.doc.academic_year || !frm.doc.curriculum_target_academic_year) {
		frappe.msgprint(__("Select the source School, source Academic Year, and target Academic Year first."));
		return;
	}
	if (frm.doc.status === STATUS_COMPLETED) {
		frappe.msgprint(__("Checklist is completed and curriculum handover is locked."));
		return;
	}

	frm.call({ method: "get_curriculum_handover_preview" })
		.then((res) => {
			const payload = res?.message || {};
			const summary = payload.summary || {};
			const message = [
				__("Prepare the next-year curriculum handover for the current scope?"),
				`<br><strong>${__("Ready to create")}:</strong> ${frappe.utils.escape_html(String(summary.ready_count || 0))}`,
				`<br><strong>${__("Already prepared")}:</strong> ${frappe.utils.escape_html(String(summary.existing_count || 0))}`,
				`<br><strong>${__("Missing target year")}:</strong> ${frappe.utils.escape_html(
					String(summary.missing_target_academic_year_count || 0)
				)}`,
			].join("");
			frappe.confirm(message, () => {
				frm.call({ method: "prepare_curriculum_handover", freeze: true })
					.then((actionRes) => {
						const result = actionRes?.message || {};
						frappe.msgprint(
							__(
								"Curriculum handover processed. Created: {0}. Failed: {1}.",
								[result.created_count || 0, result.failed_count || 0]
							)
						);
						refresh_curriculum_preview(frm);
					})
					.catch((err) => {
						frappe.msgprint(err?.message || __("Unable to prepare curriculum handover."));
					});
			});
		})
		.catch((err) => {
			frappe.msgprint(err?.message || __("Unable to preview curriculum handover."));
		});
}
