// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/schedule/doctype/end_of_year_checklist/end_of_year_checklist.js

const STATUS_COMPLETED = "Completed";

frappe.ui.form.on("End of Year Checklist", {
	refresh(frm) {
		ensure_defaults(frm);
		set_scope_queries(frm);
		refresh_scope_preview(frm);
		apply_status_rules(frm);
	},
	school(frm) {
		frm.set_value("academic_year", null);
		refresh_scope_preview(frm, { clear_on_error: true });
	},
	status(frm) {
		apply_status_rules(frm);
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
}

function apply_status_rules(frm) {
	const completed = frm.doc.status === STATUS_COMPLETED;
	const scope_ok = frm.__eoy_scope_valid !== false;
	const lock_fields = ["school", "academic_year", "status"];
	const action_buttons = [
		"archive_program_enrollment",
		"archive_student_groups",
		"archive_terms",
		"archive_academic_year",
	];

	lock_fields.forEach((fieldname) => {
		frm.set_df_property(fieldname, "read_only", completed ? 1 : 0);
	});
	action_buttons.forEach((fieldname) => {
		const locked = completed || !scope_ok;
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
		wrapper.html("<div class='text-muted'>Select a school to preview scope.</div>");
		return;
	}

	frappe.call({
		method: "ifitwala_ed.schedule.doctype.end_of_year_checklist.end_of_year_checklist.get_scope_preview",
		args: { school: frm.doc.school },
	}).then((res) => {
		const rows = res?.message?.schools || [];
		const count = res?.message?.count || rows.length;
		frm.__eoy_scope_valid = true;
		apply_status_rules(frm);
		if (!rows.length) {
			wrapper.html("<div class='text-muted'>No schools resolved for the current selection.</div>");
			return;
		}
		const list = rows
			.map((row) => frappe.utils.escape_html(row.school_name || row.name))
			.join(", ");
		const header = `<strong>${count} school${count === 1 ? "" : "s"}:</strong> `;
		wrapper.html(`<div>${header}${list}</div>`);
	}).catch((err) => {
		const message = err?.message || __("Unable to resolve school scope.");
		frm.__eoy_scope_valid = false;
		apply_status_rules(frm);
		frappe.msgprint(message);
		wrapper.html(`<div class='text-danger'>${frappe.utils.escape_html(message)}</div>`);
		if (options.clear_on_error) {
			frm.set_value("school", null);
			frm.set_value("academic_year", null);
		}
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
			const scopeLine = list ? `<br><strong>${count} school${count === 1 ? "" : "s"}:</strong> ${list}` : "";
			const message = [
				__("You are about to run an end-of-year action."),
				`<br><strong>${__("Target School")}:</strong> ${frappe.utils.escape_html(frm.doc.school)}`,
				`<br><strong>${__("Academic Year")}:</strong> ${frappe.utils.escape_html(frm.doc.academic_year)}`,
				scopeLine,
				"<br><br><strong>Warning:</strong> This is irreversible.",
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
