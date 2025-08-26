// Bootstrap JS (Popper included)
import 'bootstrap/dist/js/bootstrap.bundle.min.js';

// Portal styles (imports Bootstrap SCSS + Icons + theme)
import '../../scss/student_portal.scss';

// Feature modules (auto-registered on the global namespace)
import './student_logs';

// Collapse sidebar on mobile after clicking a link inside it
document.addEventListener('click', (e) => {
	const link = e.target.closest('#portalSidebar .nav-link');
	if (!link) return;

	const sidebar = document.querySelector('#portalSidebar');
	if (!sidebar) return;

	// Only toggle if the collapsible sidebar is currently shown (mobile)
	if (sidebar.classList.contains('show')) {
		const toggler = document.querySelector('[data-bs-target="#portalSidebar"], [data-target="#portalSidebar"]');
		if (toggler) toggler.click();
	}
});
