// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

document.addEventListener("DOMContentLoaded", function () {
  const bootstrapLoaded = typeof bootstrap !== "undefined";

  function initSchoolUI() {
    // === Carousels ===
    const schoolCarousel = document.querySelector('#schoolCarousel');
    const teamCarousel = document.querySelector('#teamCarousel');

    if (schoolCarousel) {
      new bootstrap.Carousel(schoolCarousel, {
        interval: 5000,
        ride: 'carousel'
      });
    }

    if (teamCarousel) {
      new bootstrap.Carousel(teamCarousel, {
        interval: 7000,
        ride: 'carousel',
        pause: false
      });
    }

    // === Tooltips for Leadership bios ===
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
      new bootstrap.Tooltip(el);
    });

    // === Visual polish ===
    document.querySelectorAll('img.fade-in-real-image').forEach(img => {
      img.style.opacity = 0;
      img.addEventListener('load', () => {
        img.style.transition = 'opacity 0.8s ease-in-out';
        img.style.opacity = 1;
      });
    });

    // === Lazy load: apply `.loaded` class ===
    document.querySelectorAll('img[loading="lazy"]').forEach(img => {
      img.addEventListener('load', () => {
        img.classList.add('loaded');
      });
    });
  }

  if (!bootstrapLoaded) {
    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js";
    script.crossOrigin = "anonymous";
    script.onload = initSchoolUI;
    document.head.appendChild(script);
  } else {
    initSchoolUI();
  }
});
