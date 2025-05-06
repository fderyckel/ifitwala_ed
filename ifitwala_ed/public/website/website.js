// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// Shared JS for all Ifitwala Ed public website pages
import * as bootstrap from 'bootstrap';
window.bootstrap = bootstrap;

document.addEventListener("DOMContentLoaded", function () {
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

  // === Bootstrap tooltip init ===
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => {
    new bootstrap.Tooltip(el);
  });

  document.querySelectorAll(".view-more-link").forEach(link => {
    link.addEventListener("click", e => {
      e.preventDefault();
      const target = document.getElementById(link.dataset.target);
      const expanded = target.classList.toggle("expanded");
      link.textContent = expanded ? "View less" : "View more";
    });
  });
});
