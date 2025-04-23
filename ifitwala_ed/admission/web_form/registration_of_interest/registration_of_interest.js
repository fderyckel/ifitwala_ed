frappe.ready(function () {
  // === Dynamically filter Academic Years with end_date >= today ===
	frappe.call({
		method: "ifitwala_ed.admission.web_form.registration_of_interest.registration_of_interest.get_valid_academic_years",
		callback: function (r) {
			console.log("Filtered academic years:", r.message);  // 🔍 Add this
			const fieldEl = document.querySelector('[data-fieldname="proposed_academic_year"] select');
			if (r.message && fieldEl) {
				const options = r.message.map(row =>
					`<option value="${row.name}">${row.name}</option>`
				).join("");
				fieldEl.innerHTML = `<option value="">Select...</option>` + options;
			}
		}
	});
});
