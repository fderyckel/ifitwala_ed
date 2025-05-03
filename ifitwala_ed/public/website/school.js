// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

document.addEventListener("DOMContentLoaded", function () {
  const carouselTop = document.querySelector("#schoolCarousel");
  const carouselTeam = document.querySelector("#teamCarousel");

  if (carouselTop) {
    new bootstrap.Carousel(carouselTop, {
      interval: 5000,
      ride: 'carousel',
      pause: false
    });
  }

  if (carouselTeam) {
    new bootstrap.Carousel(carouselTeam, {
      interval: 7000,
      ride: 'carousel',
      pause: false
    });
  }

  // Tooltip activation
  const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
  tooltips.forEach(el => new bootstrap.Tooltip(el));

  // Image load fade-in for smart_image macro targets
  document.querySelectorAll(".hero-img-full, .lead-circle, .object-cover").forEach((img) => {
    img.addEventListener("load", () => {
      img.classList.add("loaded");
    });
  });

  // Lazy image fade-in fallback
  document.querySelectorAll("img[loading='lazy']").forEach((img) => {
    img.addEventListener("load", () => {
      img.classList.add("loaded");
    });
  });
});
