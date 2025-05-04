// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// Specific JS for the School Web Page only — complements website.js

(function () {
  // Carousel Setup
  const schoolCarousel = document.querySelector("#schoolCarousel");
  const teamCarousel = document.querySelector("#teamCarousel");

  if (schoolCarousel) {
    new bootstrap.Carousel(schoolCarousel, {
      interval: 5000,
      ride: "carousel",
      pause: false,
    });
  }

  if (teamCarousel) {
    new bootstrap.Carousel(teamCarousel, {
      interval: 7000,
      ride: "carousel",
      pause: false,
    });
  }

  // Activate tooltips (only if not already handled globally)
  document.querySelectorAll("[data-bs-toggle='tooltip']").forEach((el) => {
    new bootstrap.Tooltip(el);
  });

  // Smart image fade-in
  document.querySelectorAll(".hero-img-full, .lead-circle, .object-cover").forEach((img) => {
    img.addEventListener("load", () => {
      img.classList.add("loaded");
    });
  });

  // Fallback lazy-load polish
  document.querySelectorAll("img[loading='lazy']").forEach((img) => {
    img.addEventListener("load", () => {
      img.classList.add("loaded");
    });
  });
})();

