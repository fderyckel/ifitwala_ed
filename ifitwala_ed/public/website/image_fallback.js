// image_fallback.js

document.addEventListener("DOMContentLoaded", function () {
  const images = document.querySelectorAll(".hero-img-full");

  images.forEach(img => {
    const srcLarge = img.getAttribute("src");
    const srcMedium = img.dataset.srcMedium;
    const srcOriginal = img.dataset.srcOriginal;

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
