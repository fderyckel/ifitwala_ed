// image_fallback.js

document.addEventListener("DOMContentLoaded", function () {
  const images = document.querySelectorAll(".hero-img-full");

  images.forEach(img => {
    // Resolve relative → absolute URL
    const srcLarge = new URL(img.getAttribute("src"), window.location.origin).href;
    const srcMedium = img.dataset.srcMedium
      ? new URL(img.dataset.srcMedium, window.location.origin).href
      : null;
    const srcOriginal = img.dataset.srcOriginal
      ? new URL(img.dataset.srcOriginal, window.location.origin).href
      : null;

    console.debug("[Image Load] Trying:", srcLarge);

    img.addEventListener("load", () => {
      console.debug("[Image Load] Success:", img.src);
      img.classList.add("loaded");
    });

    img.addEventListener("error", () => {
      if (img.src === srcLarge && srcMedium) {
        console.warn("[Fallback] Large failed. Trying medium:", srcMedium);
        img.src = srcMedium;
      } else if (img.src === srcMedium && srcOriginal) {
        console.warn("[Fallback] Medium failed. Trying original:", srcOriginal);
        img.src = srcOriginal;
      } else {
        console.error("[Fallback] All image sources failed for:", img.alt || img);
      }
    });
  });
});

