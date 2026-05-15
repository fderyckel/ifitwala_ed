// ifitwala_ed/public/website/blocks/staff_directory.js

function pluralizePeopleCount(count) {
	return `${count} ${count === 1 ? 'person' : 'people'}`;
}

function initStaffDirectory(directory) {
	const cards = Array.from(directory.querySelectorAll('[data-directory-card]'));
	if (!cards.length) {
		return;
	}

	const searchInput = directory.querySelector('[data-directory-search]');
	const designationSelect = directory.querySelector('[data-directory-designation]');
	const roleProfileSelect = directory.querySelector('[data-directory-role-profile]');
	const countHost = directory.querySelector('[data-directory-count]');
	const noResults = directory.querySelector('[data-directory-no-results]');

	const applyFilters = () => {
		const query = String(searchInput?.value || '')
			.trim()
			.toLowerCase();
		const designation = String(designationSelect?.value || '')
			.trim()
			.toLowerCase();
		const roleProfile = String(roleProfileSelect?.value || '')
			.trim()
			.toLowerCase();

		let visibleCount = 0;
		for (const card of cards) {
			const searchText = String(card.dataset.searchText || '').toLowerCase();
			const cardDesignation = String(card.dataset.designation || '').toLowerCase();
			const cardRoleProfile = String(card.dataset.roleProfile || '').toLowerCase();

			const matchesQuery = !query || searchText.includes(query);
			const matchesDesignation = !designation || cardDesignation === designation;
			const matchesRoleProfile = !roleProfile || cardRoleProfile === roleProfile;
			const isVisible = matchesQuery && matchesDesignation && matchesRoleProfile;

			card.classList.toggle('hidden', !isVisible);
			if (isVisible) {
				visibleCount += 1;
			}
		}

		if (countHost) {
			countHost.textContent = pluralizePeopleCount(visibleCount);
		}
		if (noResults) {
			noResults.classList.toggle('hidden', visibleCount !== 0);
		}
	};

	searchInput?.addEventListener('input', applyFilters);
	designationSelect?.addEventListener('change', applyFilters);
	roleProfileSelect?.addEventListener('change', applyFilters);

	applyFilters();
}

document.addEventListener('DOMContentLoaded', () => {
	document.querySelectorAll('[data-staff-directory]').forEach(initStaffDirectory);
});
