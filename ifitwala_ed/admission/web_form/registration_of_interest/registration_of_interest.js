frappe.ready(function () {
  // === Banner logic (unchanged) ===
  const bannerImage = frappe.web_form.web_form.banner_image;
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
    method: "frappe.client.get_list",
    args: {
      doctype: "Academic Year",
      filters: [
        ["end_date", ">=", frappe.datetime.get_today()]
      ],
      fields: ["name"],
      order_by: "start_date asc"
    },
    callback: function (r) {
      if (r.message) {
        const options = r.message.map(row => `<option value="${row.name}">${row.name}</option>`).join("");
        const fieldEl = document.querySelector('[data-fieldname="proposed_academic_year"] select');

        if (fieldEl) {
          fieldEl.innerHTML = `<option value="">Select...</option>` + options;
        }
      }
    }
  });
});
