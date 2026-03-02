// ifitwala_ed/public/website/blocks/section_carousel.js

function initSectionCarousel(carousel) {
	const slides = Array.from(carousel.querySelectorAll('[data-section-carousel-slide]'));
	if (slides.length <= 1) {
		return;
	}

	const dots = Array.from(carousel.querySelectorAll('[data-section-carousel-dot]'));
	let currentIndex = slides.findIndex(slide => slide.classList.contains('opacity-100'));
	if (currentIndex < 0) {
		currentIndex = 0;
	}

	const setSlide = index => {
		if (index === currentIndex || index < 0 || index >= slides.length) {
			return;
		}
		slides[currentIndex].classList.add('opacity-0', 'z-0');
		slides[currentIndex].classList.remove('opacity-100', 'z-10');
		if (dots[currentIndex]) {
			dots[currentIndex].classList.remove('ring-1', 'ring-white');
		}

		currentIndex = index;
		slides[currentIndex].classList.add('opacity-100', 'z-10');
		slides[currentIndex].classList.remove('opacity-0', 'z-0');
		if (dots[currentIndex]) {
			dots[currentIndex].classList.add('ring-1', 'ring-white');
		}
	};

	const next = () => setSlide((currentIndex + 1) % slides.length);
	const prev = () => setSlide((currentIndex - 1 + slides.length) % slides.length);

	const nextBtn = carousel.querySelector('[data-section-carousel-next]');
	const prevBtn = carousel.querySelector('[data-section-carousel-prev]');
	if (nextBtn) {
		nextBtn.addEventListener('click', next);
	}
	if (prevBtn) {
		prevBtn.addEventListener('click', prev);
	}

	dots.forEach((dot, idx) => {
		dot.addEventListener('click', () => setSlide(idx));
	});

	const intervalMs = Number.parseInt(carousel.dataset.interval || '5000', 10);
	const autoplayEnabled = !['false', 'False', '0'].includes(carousel.dataset.autoplay || 'true');
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

	carousel.addEventListener('mouseenter', stopAutoplay);
	carousel.addEventListener('mouseleave', startAutoplay);
	carousel.addEventListener('focusin', stopAutoplay);
	carousel.addEventListener('focusout', () => {
		if (!carousel.contains(document.activeElement)) {
			startAutoplay();
		}
	});
	document.addEventListener('visibilitychange', () => {
		if (document.hidden) {
			stopAutoplay();
			return;
		}
		startAutoplay();
	});

	startAutoplay();
}

document.addEventListener('DOMContentLoaded', () => {
	document.querySelectorAll('[data-section-carousel]').forEach(initSectionCarousel);
});
