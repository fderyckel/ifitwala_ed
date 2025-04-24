// admission/web_form/registration_of_interest/registration_of_interest.js
// --------------------------------------------------------------------
console.log("≡ RoI script LOADED");

frappe.ready(function () {
	// ────── step 1/2 ──────
	console.log("[RoI] frappe.ready fired – attaching hooks …");

	// Show when the form HTML is in the DOM
	frappe.web_form.events.on("after_load", () => {
		console.log("[RoI] after_load – form rendered");
	});

	// 🔑  Attach dynamic filter to the Link field
	frappe.web_form.set_query("proposed_academic_year", function () {
		const today = frappe.datetime.get_today();
		const filters = [
			["Academic Year", "year_end_date", ">=", today]
		];
		console.log("[RoI] set_query invoked – returning", filters);
		return { filters };
	});

	console.log("[RoI] hooks attached – ready!");
});
