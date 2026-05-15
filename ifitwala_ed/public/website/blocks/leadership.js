// ifitwala_ed/public/website/blocks/leadership.js

function initPeopleCarousel(carousel) {
	const track = carousel.querySelector('[data-people-carousel-track]');
	if (!track) {
		return;
	}

	const prevButton = carousel.querySelector('[data-people-carousel-prev]');
	const nextButton = carousel.querySelector('[data-people-carousel-next]');
	const dotsHost = carousel.querySelector('[data-people-carousel-dots]');
	const resizeObserverSupported = typeof window.ResizeObserver !== 'undefined';
	let dots = [];
	let pageCount = 1;
	let currentPage = 0;
	let rafId = null;

	const getStepWidth = () => Math.max(track.clientWidth * 0.92, 1);

	const computePageCount = () => {
		const maxScroll = Math.max(track.scrollWidth - track.clientWidth, 0);
		if (maxScroll <= 8) {
			return 1;
		}
		return Math.max(1, Math.ceil(maxScroll / getStepWidth()) + 1);
	};

	const setPage = (index, behavior = 'smooth') => {
		const nextIndex = Math.max(0, Math.min(index, pageCount - 1));
		track.scrollTo({
			left: nextIndex * getStepWidth(),
			behavior,
		});
	};

	const syncState = () => {
		pageCount = computePageCount();
		currentPage =
			pageCount <= 1
				? 0
				: Math.max(0, Math.min(pageCount - 1, Math.round(track.scrollLeft / getStepWidth())));

		if (prevButton) {
			prevButton.disabled = currentPage <= 0;
			prevButton.classList.toggle('hidden', pageCount <= 1);
		}
		if (nextButton) {
			nextButton.disabled = currentPage >= pageCount - 1;
			nextButton.classList.toggle('hidden', pageCount <= 1);
		}
		if (dotsHost) {
			dotsHost.classList.toggle('hidden', pageCount <= 1);
		}
		dots.forEach((dot, index) => {
			const isActive = index === currentPage;
			dot.classList.toggle('is-active', isActive);
			dot.setAttribute('aria-current', isActive ? 'true' : 'false');
		});
	};

	const renderDots = () => {
		if (!dotsHost) {
			return;
		}

		pageCount = computePageCount();
		dotsHost.innerHTML = '';
		dots = [];
		for (let index = 0; index < pageCount; index += 1) {
			const button = document.createElement('button');
			button.type = 'button';
			button.className = 'site-people-dot h-2.5 w-2.5 rounded-full bg-slate-300 transition';
			button.setAttribute('aria-label', `Go to slide ${index + 1}`);
			button.addEventListener('click', () => setPage(index));
			dotsHost.appendChild(button);
			dots.push(button);
		}
	};

	const handleScroll = () => {
		if (rafId) {
			window.cancelAnimationFrame(rafId);
		}
		rafId = window.requestAnimationFrame(syncState);
	};

	if (prevButton) {
		prevButton.addEventListener('click', () => setPage(currentPage - 1));
	}
	if (nextButton) {
		nextButton.addEventListener('click', () => setPage(currentPage + 1));
	}

	track.addEventListener('scroll', handleScroll, { passive: true });
	track.addEventListener('keydown', event => {
		if (event.key === 'ArrowRight') {
			event.preventDefault();
			setPage(currentPage + 1);
		}
		if (event.key === 'ArrowLeft') {
			event.preventDefault();
			setPage(currentPage - 1);
		}
	});

	if (resizeObserverSupported) {
		const observer = new window.ResizeObserver(() => {
			renderDots();
			syncState();
		});
		observer.observe(track);
	} else {
		window.addEventListener('resize', () => {
			renderDots();
			syncState();
		});
	}

	renderDots();
	syncState();
}

document.addEventListener('DOMContentLoaded', () => {
	document.querySelectorAll('[data-people-carousel]').forEach(initPeopleCarousel);
});
