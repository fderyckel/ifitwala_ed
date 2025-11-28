// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/public/website/image_fallback.js

document.addEventListener("DOMContentLoaded", () => {
  for (const img of document.querySelectorAll("img[fallback='carousel']")) {
    // Grab all candidate URLs once
    const card     = img.dataset.srcCard    || null;
    const medium   = img.dataset.srcMedium  || null;
    const hero     = img.dataset.srcHero    || null;
    const original = img.dataset.srcOriginal|| null;

    // Build our progressive chain
    const chain = [];
    if (card) {
      chain.push(card);
      if (medium) chain.push(medium);
      if (hero)   chain.push(hero);
    } else if (original) {
      chain.push(original);
    }

    let idx = 0;
    // Kick things off with the very first URL
    if (chain[0]) {
      img.src = chain[0];
    }

    // On successful load → auto-advance to next
    img.addEventListener("load", () => {
      img.classList.add("loaded");
      if (idx + 1 < chain.length) {
        img.src = chain[++idx];
      }
    }, { once: true });

    // On error → revert one step (if possible) and stop listening
    img.addEventListener("error", () => {
      if (idx > 0) {
        img.src = chain[--idx];
      }
    }, { once: true });
  }
});
