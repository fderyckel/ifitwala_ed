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

frappe.ui.form.on("Program Enrollment Request", {
	refresh(frm) {
		setAcademicYearQuery(frm);
		syncAcademicYearState(frm);
	},

	program_offering(frm) {
		syncAcademicYearState(frm);
	},
});
