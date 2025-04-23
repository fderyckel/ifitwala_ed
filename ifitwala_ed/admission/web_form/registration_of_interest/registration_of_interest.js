frappe.ready(function () {
  // === Banner logic (unchanged) ===
  const bannerImage = frappe.web_form.banner_image;
  const bannerContainer = document.querySelector('.page-banner');
  if (bannerImage && bannerContainer) {
    bannerContainer.style.background = 'none';
    bannerContainer.style.height = 'auto';
    bannerContainer.style.padding = '0';
    const img = document.createElement('img');
    img.src = bannerImage;
    img.alt = "Ifitwala Banner";
    img.style.display = 'block';
    img.style.width = '100%';
    img.style.height = 'auto';
    img.style.objectFit = 'contain';
    img.style.marginBottom = '0.5rem';
    bannerContainer.innerHTML = '';
    bannerContainer.appendChild(img);
  }

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
