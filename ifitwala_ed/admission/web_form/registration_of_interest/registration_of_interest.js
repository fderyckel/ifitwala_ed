// apps/ifitwala_ed/ifitwala_ed/admission/web_form/registration_of_interest/registration_of_interest.js
// --------------------------------------------------------------------
console.log("≡ RoI script LOADED");

frappe.ready(function () {
	// ───────────────── step 1 ─────────────────
	console.log("[RoI] frappe.ready – initialising hooks …");

	// Fires once the Web-Form HTML is in the DOM
	frappe.web_form.events.on("after_load", () => {
		console.log("[RoI] after_load – form rendered");

		const field = frappe.web_form.fields_dict["proposed_academic_year"];
		if (!field) {
			console.warn("[RoI] ❗ field object not found");
			return;
		}

		console.log("[RoI] attaching dynamic get_query to proposed_academic_year");

		field.get_query = () => {
			const today = frappe.datetime.get_today();
			const filters = [
				["Academic Year", "year_end_date", ">=", today]
			];
			console.log("[RoI] get_query invoked – returning filters →", filters);
			return { filters };
		};
	});

	console.log("[RoI] hooks wired – waiting for after_load …");
});
