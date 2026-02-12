// ifitwala_ed/public/website/blocks/admission_cta.js

function emitAdmissionCtaEvent(link) {
	const detail = {
		intent: link.dataset.intent || null,
		tracking_id: link.dataset.trackingId || null,
		href: link.getAttribute("href") || null,
		ts: Date.now(),
	};
	window.dispatchEvent(new CustomEvent("ifitwala:admission-cta-click", { detail }));
}

function initAdmissionCtaEmphasis() {
	const ctaLinks = Array.from(document.querySelectorAll("[data-admission-cta] .site-cta-link"));
	if (!ctaLinks.length) {
		return;
	}

	ctaLinks.forEach((link) => {
		link.addEventListener("click", () => emitAdmissionCtaEvent(link));
	});

	const motionEnabled = (document.body.dataset.themeMotion || "on") !== "off";
	if (!motionEnabled || typeof window.IntersectionObserver === "undefined") {
		return;
	}

	const observer = new IntersectionObserver(
		(entries) => {
			entries.forEach((entry) => {
				if (!entry.isIntersecting) {
					return;
				}
				entry.target.classList.add("is-emphasized");
				observer.unobserve(entry.target);
			});
		},
		{
			threshold: 0.6,
		}
	);

	ctaLinks.forEach((link) => observer.observe(link));
}

document.addEventListener("DOMContentLoaded", initAdmissionCtaEmphasis);
