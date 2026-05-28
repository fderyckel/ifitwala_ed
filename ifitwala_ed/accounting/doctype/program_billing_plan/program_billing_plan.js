const GET_PROGRAM_OFFERING_ACADEMIC_YEARS =
	"ifitwala_ed.accounting.doctype.program_billing_plan.program_billing_plan.get_program_offering_academic_years";

function set_academic_year_query(frm) {
	frm.set_query("academic_year", () => {
		const academicYears = frm._program_billing_plan_academic_years || [];
		if (academicYears.length) {
			return {
				filters: { name: ["in", academicYears] },
				order_by: "year_start_date desc",
			};
		}

		return { filters: { name: ["=", "___NONE___"] } };
	});
}

async function load_program_offering_academic_years(frm) {
	if (!frm.doc.program_offering) {
		frm._program_billing_plan_academic_years = [];
		return [];
	}

	const response = await frappe.call({
		method: GET_PROGRAM_OFFERING_ACADEMIC_YEARS,
		args: {
			program_offering: frm.doc.program_offering,
			organization: frm.doc.organization || null,
		},
	});
	const rows = response.message || [];
	frm._program_billing_plan_academic_years = rows
		.map((row) => row.academic_year)
		.filter((academicYear) => Boolean(academicYear));
	return frm._program_billing_plan_academic_years;
}

async function sync_academic_year_state(frm) {
	const academicYears = await load_program_offering_academic_years(frm);
	const hasOffering = Boolean(frm.doc.program_offering);
	const singleAcademicYear = hasOffering && academicYears.length === 1;

	frm.set_df_property("academic_year", "read_only", !hasOffering || singleAcademicYear ? 1 : 0);
	frm.set_df_property(
		"academic_year",
		"description",
		hasOffering
			? __("Academic Year must be one of the years configured on the selected Program Offering.")
			: __("Select Program Offering first.")
	);

	if (!hasOffering) {
		if (frm.doc.academic_year) {
			await frm.set_value("academic_year", null);
		}
		frm.refresh_field("academic_year");
		return;
	}

	if (frm.doc.academic_year && !academicYears.includes(frm.doc.academic_year)) {
		await frm.set_value("academic_year", null);
		frappe.show_alert({
			message: __("Academic Year was cleared because it is not part of the selected Program Offering."),
			indicator: "orange",
		});
	}

	if (!frm.doc.academic_year && singleAcademicYear) {
		await frm.set_value("academic_year", academicYears[0]);
	}

	frm.refresh_field("academic_year");
}

frappe.ui.form.on("Program Billing Plan", {
	setup(frm) {
		set_academic_year_query(frm);
	},

	onload(frm) {
		set_academic_year_query(frm);
		sync_academic_year_state(frm);
	},

	refresh(frm) {
		set_academic_year_query(frm);
		sync_academic_year_state(frm);

		if (!frm.is_new()) {
			frm.add_custom_button(__("Generate Billing Schedules"), async () => {
				const r = await frappe.call(
					"ifitwala_ed.accounting.doctype.program_billing_plan.program_billing_plan.generate_billing_schedules",
					{ program_billing_plan: frm.doc.name }
				);
				const message = r.message || {};
				frappe.msgprint(
					__("Generated or refreshed {0} billing schedules.", [message.schedule_names?.length || 0])
				);
			});
		}
	},

	program_offering(frm) {
		sync_academic_year_state(frm);
	},

	organization(frm) {
		sync_academic_year_state(frm);
	},
});
