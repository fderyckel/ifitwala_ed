// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/public/website/website.js

function initNavigationToggle() {
	const navToggle = document.querySelector('[data-site-nav-toggle]');
	const navPanel = document.querySelector('[data-site-nav-panel]');
	if (!navToggle || !navPanel) {
		return;
	}

	const desktopMedia = window.matchMedia('(min-width: 1024px)');

	function setExpanded(expanded) {
		navToggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
		navPanel.classList.toggle('hidden', !expanded);
	}

	function closePanel() {
		setExpanded(false);
	}

	navToggle.addEventListener('click', () => {
		const expanded = navToggle.getAttribute('aria-expanded') === 'true';
		setExpanded(!expanded);
	});

	navPanel.querySelectorAll('a').forEach(link => {
		link.addEventListener('click', closePanel);
	});

	document.addEventListener('keydown', event => {
		if (event.key === 'Escape') {
			closePanel();
		}
	});

	if (typeof desktopMedia.addEventListener === 'function') {
		desktopMedia.addEventListener('change', event => {
			if (event.matches) {
				closePanel();
			}
		});
	} else if (typeof desktopMedia.addListener === 'function') {
		desktopMedia.addListener(event => {
			if (event.matches) {
				closePanel();
			}
		});
	}
}

function initLazyImagePolish() {
	const imageNodes = document.querySelectorAll(
		"img[loading='lazy'], img[fallback='carousel'], .hero-img-full, .lead-circle, .object-cover"
	);

	imageNodes.forEach(img => {
		img.addEventListener('load', () => {
			img.classList.add('loaded');
		});
		if (img.complete) {
			img.classList.add('loaded');
		}
	});
}

function initViewMoreToggles() {
	document.querySelectorAll('.view-more-link').forEach(link => {
		link.addEventListener('click', event => {
			event.preventDefault();
			const target = document.getElementById(link.dataset.target);
			if (!target) {
				return;
			}
			const expanded = target.classList.toggle('expanded');
			link.textContent = expanded ? 'View less' : 'View more';
		});
	});
}

function initRevealAnimations() {
	const revealNodes = Array.from(document.querySelectorAll('[data-reveal]'));
	if (!revealNodes.length) {
		return;
	}

	const motionEnabled = (document.body.dataset.themeMotion || 'on') !== 'off';
	revealNodes.forEach(node => {
		const index = Number.parseInt(node.dataset.revealIndex || '0', 10) || 0;
		const delayMs = Math.min(index * 70, 420);
		node.style.setProperty('--if-reveal-delay', `${delayMs}ms`);
		node.classList.add('reveal-ready');
	});

	if (!motionEnabled || typeof window.IntersectionObserver === 'undefined') {
		revealNodes.forEach(node => node.classList.add('is-revealed'));
		return;
	}

	const observer = new IntersectionObserver(
		entries => {
			entries.forEach(entry => {
				if (!entry.isIntersecting) {
					return;
				}
				entry.target.classList.add('is-revealed');
				observer.unobserve(entry.target);
			});
		},
		{
			threshold: 0.12,
			rootMargin: '0px 0px -8% 0px',
		}
	);

	revealNodes.forEach(node => observer.observe(node));
}

document.addEventListener('DOMContentLoaded', () => {
	initNavigationToggle();
	initLazyImagePolish();
	initViewMoreToggles();
	initRevealAnimations();
});
