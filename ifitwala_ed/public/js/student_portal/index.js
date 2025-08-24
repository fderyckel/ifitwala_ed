// Bootstrap JS (Popper included)
import 'bootstrap/dist/js/bootstrap.bundle.min.js';

// Portal styles (imports Bootstrap SCSS + Icons + theme)
import '../../scss/student_portal.scss';

// Optional: collapse sidebar on mobile after clicking a link
document.addEventListener('click', (e) => {
	const link = e.target.closest('#portalSidebar .nav-link');
	if (!link) return;
	const sidebar = document.querySelector('#portalSidebar');
	if (sidebar && getComputedStyle(sidebar).display !== 'block') {
		const toggler = document.querySelector('[data-bs-target="#portalSidebar"]');
		if (toggler) toggler.click();
	}
});
