// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

const ACTIVATION_MODE_ACADEMIC_YEAR_START = "Academic Year Start";

frappe.ui.form.on("Course Plan", {
	refresh(frm) {
		refreshRolloverActions(frm);
		refreshActivationIntro(frm);
	},
	academic_year(frm) {
		refreshActivationIntro(frm);
	},
	activation_mode(frm) {
		refreshActivationIntro(frm);
	},
});

function refreshRolloverActions(frm) {
	if (frm.is_new() || !frm.doc.course || frm.doc.plan_status === "Archived") {
		return;
	}
	frm.add_custom_button(__("Create Next Academic Year Plan"), () => openRolloverDialog(frm));
}

function openRolloverDialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Create Next Academic Year Plan"),
		fields: [
			{
				fieldname: "target_academic_year",
				fieldtype: "Link",
				label: __("Target Academic Year"),
				options: "Academic Year",
				reqd: 1,
				get_query: () => ({
					query: "ifitwala_ed.curriculum.doctype.course_plan.course_plan.rollover_academic_year_link_query",
					filters: { course_plan: frm.doc.name },
				}),
			},
			{
				fieldname: "activation_mode",
				fieldtype: "Select",
				label: __("Activation Mode"),
				options: "Manual\nAcademic Year Start",
				default: ACTIVATION_MODE_ACADEMIC_YEAR_START,
			},
			{
				fieldname: "copy_plan_resources",
				fieldtype: "Check",
				label: __("Copy shared course resources"),
				default: 1,
			},
			{
				fieldname: "copy_unit_resources",
				fieldtype: "Check",
				label: __("Copy shared unit resources"),
				default: 1,
			},
		],
		primary_action_label: __("Create Rollover Plan"),
		primary_action(values) {
			frappe.call({
				method: "ifitwala_ed.curriculum.doctype.course_plan.course_plan.create_rollover_course_plan",
				args: {
					course_plan: frm.doc.name,
					target_academic_year: values.target_academic_year,
					activation_mode: values.activation_mode,
					copy_plan_resources: values.copy_plan_resources,
					copy_unit_resources: values.copy_unit_resources,
				},
				freeze: true,
				freeze_message: __("Creating the next academic year course plan..."),
			})
				.then((res) => {
					const payload = res?.message || {};
					dialog.hide();
					frappe.show_alert(
						{
							message: __(
								"Created {0} with {1} unit(s), {2} course resource(s), and {3} unit resource placement(s).",
								[
									payload.course_plan || __("the new course plan"),
									payload.units_created || 0,
									payload.plan_resources_copied || 0,
									payload.unit_resources_copied || 0,
								]
							),
							indicator: "green",
						},
						7
					);
					frappe.set_route("Form", "Course Plan", payload.course_plan);
				})
				.catch((err) => {
					frappe.msgprint(err?.message || __("Unable to create the rollover course plan."));
				});
		},
	});
	dialog.show();
}

async function refreshActivationIntro(frm) {
	if (typeof frm.set_intro !== "function") return;
	if (
		frm.doc.plan_status !== "Draft" ||
		frm.doc.activation_mode !== ACTIVATION_MODE_ACADEMIC_YEAR_START ||
		!frm.doc.academic_year
	) {
		frm.set_intro("");
		return;
	}

	try {
		const { message } = await frappe.db.get_value("Academic Year", frm.doc.academic_year, "year_start_date");
		const startDate = message?.year_start_date;
		if (!startDate) {
			frm.set_intro(
				__("This draft is scheduled to activate automatically once the linked Academic Year has a start date."),
				"orange"
			);
			return;
		}
		frm.set_intro(
			__("This draft will activate automatically on the Academic Year start date: {0}.", [
				frappe.datetime.str_to_user(startDate),
			]),
			"blue"
		);
	} catch (_err) {
		frm.set_intro(__("Unable to resolve the Academic Year start date for this scheduled activation."), "orange");
	}
}
