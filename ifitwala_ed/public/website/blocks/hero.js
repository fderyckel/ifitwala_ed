// ifitwala_ed/public/website/blocks/hero.js

function initHeroCarousel(carousel) {
	const slides = Array.from(carousel.querySelectorAll("[data-carousel-slide]"));
	if (slides.length <= 1) {
		return;
	}

	let currentIndex = slides.findIndex((slide) => slide.classList.contains("opacity-100"));
	if (currentIndex < 0) {
		currentIndex = 0;
	}

	const setSlide = (index) => {
		slides[currentIndex].classList.add("opacity-0", "z-0");
		slides[currentIndex].classList.remove("opacity-100", "z-10");
		currentIndex = index;
		slides[currentIndex].classList.add("opacity-100", "z-10");
		slides[currentIndex].classList.remove("opacity-0", "z-0");
	};

	const next = () => setSlide((currentIndex + 1) % slides.length);
	const prev = () => setSlide((currentIndex - 1 + slides.length) % slides.length);

	const nextBtn = carousel.querySelector("[data-carousel-next]");
	const prevBtn = carousel.querySelector("[data-carousel-prev]");
	if (nextBtn) {
		nextBtn.addEventListener("click", next);
	}
	if (prevBtn) {
		prevBtn.addEventListener("click", prev);
	}

	const intervalMs = Number.parseInt(carousel.dataset.interval || "5000", 10);
	const autoplayEnabled = !["false", "False", "0"].includes(carousel.dataset.autoplay || "true");
	if (!autoplayEnabled) {
		return;
	}

	let timer = null;
	const stopAutoplay = () => {
		if (timer) {
			window.clearInterval(timer);
			timer = null;
		}
	};
	const startAutoplay = () => {
		stopAutoplay();
		timer = window.setInterval(next, Number.isFinite(intervalMs) ? intervalMs : 5000);
	};

	carousel.addEventListener("mouseenter", stopAutoplay);
	carousel.addEventListener("mouseleave", startAutoplay);
	carousel.addEventListener("focusin", stopAutoplay);
	carousel.addEventListener("focusout", () => {
		if (!carousel.contains(document.activeElement)) {
			startAutoplay();
		}
	});
	document.addEventListener("visibilitychange", () => {
		if (document.hidden) {
			stopAutoplay();
			return;
		}
		startAutoplay();
	});

	startAutoplay();
}

document.addEventListener("DOMContentLoaded", () => {
	document.querySelectorAll("[data-carousel]").forEach(initHeroCarousel);
});
