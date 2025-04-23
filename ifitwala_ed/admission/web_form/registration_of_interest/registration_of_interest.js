frappe.ready(function () {
	frappe.ready(function () {
		frappe.web_form.after_render = () => {
			// Retry logic in case the field hasn't rendered yet
			const tryUpdateDropdown = () => {
				const fieldEl = document.querySelector('[data-fieldname="proposed_academic_year"] select');
	
				if (fieldEl) {
					frappe.call({
						method: "ifitwala_ed.admission.web_form.registration_of_interest.registration_of_interest.get_valid_academic_years",
						callback: function (r) {
							console.log("Filtered academic years:", r.message);
							const options = r.message.map(row =>
								`<option value="${row.name}">${row.name}</option>`
							).join("");
							fieldEl.innerHTML = `<option value="">Select...</option>` + options;
						}
					});
				} else {
					// Retry after a short delay
					console.log("Dropdown not yet rendered, retrying...");
					setTimeout(tryUpdateDropdown, 100);
				}
			};
	
			tryUpdateDropdown();
		};
	});
	
});
