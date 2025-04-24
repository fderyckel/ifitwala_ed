// apps/ifitwala_ed/ifitwala_ed/admission/web_form/registration_of_interest/registration_of_interest.js
// --------------------------------------------------------------------
console.log("≡ RoI script LOADED");

frappe.ready(function () {
	console.log("[RoI] frappe.ready – wiring hooks …");

	// Fires once all fields are in the DOM
	frappe.web_form.events.on("after_load", () => {
		console.log("[RoI] after_load – form rendered");

		// Grab the Link control object
		const ac_year = frappe.web_form.get_field("proposed_academic_year");
		if (!ac_year) {
			console.warn("[RoI] ❗ proposed_academic_year control not found");
			return;
		}

		console.log("[RoI] attaching ac_year.set_query …");
		ac_year.set_query(() => {
			const today   = frappe.datetime.get_today();
			const filters = [
				["Academic Year", "year_end_date", ">=", today]
			];
			console.log("[RoI] set_query invoked – returning", filters);
			return { filters };
		});
	});

	console.log("[RoI] hooks wired – awaiting after_load");
});
