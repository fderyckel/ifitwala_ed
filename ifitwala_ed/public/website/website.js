// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// Shared JS for all Ifitwala Ed public website pages

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

  // === Bootstrap fallback loader ===
  if (typeof bootstrap === "undefined") {
    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js";
    script.crossOrigin = "anonymous";
    document.head.appendChild(script);
  }
});
