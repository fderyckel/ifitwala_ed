// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// Shared JS for all Ifitwala Ed public website pages.

document.addEventListener("DOMContentLoaded", function () {
  const navToggle = document.querySelector("[data-site-nav-toggle]");
  const navPanel = document.querySelector("[data-site-nav-panel]");
  if (navToggle && navPanel) {
    navToggle.addEventListener("click", () => {
      const expanded = navToggle.getAttribute("aria-expanded") === "true";
      navToggle.setAttribute("aria-expanded", expanded ? "false" : "true");
      navPanel.classList.toggle("hidden", expanded);
    });
  }

  // === Lazy-loaded image polish ===
  document.querySelectorAll("img[loading='lazy']").forEach((img) => {
    img.addEventListener("load", () => {
      img.classList.add("loaded");
    });
  });

  // === Smart image fade-in targets ===
  document.querySelectorAll(".hero-img-full, .lead-circle, .object-cover").forEach((img) => {
    img.addEventListener("load", () => {
      img.classList.add("loaded");
    });
  });

  document.querySelectorAll(".view-more-link").forEach(link => {
    link.addEventListener("click", e => {
      e.preventDefault();
      const target = document.getElementById(link.dataset.target);
      const expanded = target.classList.toggle("expanded");
      link.textContent = expanded ? "View less" : "View more";
    });
  });

  const carousels = document.querySelectorAll("[data-carousel]");
  carousels.forEach((carousel) => {
    const slides = Array.from(carousel.querySelectorAll("[data-carousel-slide]"));
    if (!slides.length) {
      return;
    }

    let current = slides.findIndex((slide) => slide.classList.contains("opacity-100"));
    if (current < 0) {
      current = 0;
      slides[0].classList.add("opacity-100", "z-10");
      slides[0].classList.remove("opacity-0", "z-0");
    }

    const interval = parseInt(carousel.dataset.interval || "5000", 10);
    const autoplay = carousel.dataset.autoplay !== "False" && carousel.dataset.autoplay !== "false";

    const showSlide = (index) => {
      slides[current].classList.add("opacity-0", "z-0");
      slides[current].classList.remove("opacity-100", "z-10");
      current = index;
      slides[current].classList.add("opacity-100", "z-10");
      slides[current].classList.remove("opacity-0", "z-0");
    };

    const next = () => showSlide((current + 1) % slides.length);
    const prev = () => showSlide((current - 1 + slides.length) % slides.length);

    const nextBtn = carousel.querySelector("[data-carousel-next]");
    const prevBtn = carousel.querySelector("[data-carousel-prev]");
    if (nextBtn) nextBtn.addEventListener("click", next);
    if (prevBtn) prevBtn.addEventListener("click", prev);

    if (autoplay) {
      let timer = setInterval(next, interval);
      carousel.addEventListener("mouseenter", () => clearInterval(timer));
      carousel.addEventListener("mouseleave", () => {
        timer = setInterval(next, interval);
      });
    }
  });
});
