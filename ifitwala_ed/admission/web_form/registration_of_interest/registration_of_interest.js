frappe.ready(function () {
  // Grab the banner image URL from the webform settings
  const bannerImage = frappe.web_form.web_form.banner_image;

  if (bannerImage) {
    const bannerContainer = document.querySelector('.page-banner');
    if (bannerContainer) {
      // Reset styles to prevent cropping
      bannerContainer.style.background = 'none';
      bannerContainer.style.height = 'auto';
      bannerContainer.style.padding = '0';

      // Inject full image
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
  }

  // Apply dynamic filter to Proposed Academic Year
  frappe.web_form.set_query("proposed_academic_year", () => {
    return {
      filters: [
        ["Academic Year", "year_end_date", ">=", frappe.datetime.get_today()]
      ]
    };
  });

});
