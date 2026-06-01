// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/public/website/people_profiles.js

(function () {
	if (window.IfitwalaPeopleProfiles) {
		return;
	}

	let peopleProfileDialogState = null;
	let peopleProfileDialogClickListenerReady = false;

	function onReady(callback) {
		if (document.readyState === 'loading') {
			document.addEventListener('DOMContentLoaded', callback, { once: true });
			return;
		}
		callback();
	}

	function applyPeoplePhotoFrameStyles(root = document) {
		root.querySelectorAll('.site-people-photo-frame').forEach(frame => {
			frame.style.position = 'relative';
			frame.style.width = '100%';
			frame.style.aspectRatio = '1 / 1';
			frame.style.flex = '0 0 auto';
			frame.style.overflow = 'hidden';
		});

		root
			.querySelectorAll('.site-people-photo-frame > img, .site-people-photo-image')
			.forEach(image => {
				image.style.display = 'block';
				image.style.width = '100%';
				image.style.height = '100%';
				image.style.objectFit = 'cover';
				image.style.pointerEvents = 'none';
			});

		root.querySelectorAll('.site-people-photo-fallback').forEach(fallback => {
			fallback.style.width = '100%';
			fallback.style.height = '100%';
		});
	}

	function createPeopleProfileDialog() {
		const dialog = document.createElement('div');
		dialog.className = 'site-people-dialog';
		dialog.setAttribute('aria-hidden', 'true');
		dialog.innerHTML = `
			<div class="site-people-dialog__backdrop" data-person-dialog-backdrop></div>
			<section class="site-people-dialog__panel" role="dialog" aria-modal="true" aria-labelledby="site-people-dialog-title" aria-describedby="site-people-dialog-bio">
				<button type="button" class="site-people-dialog__close" data-person-dialog-close aria-label="Close profile">&times;</button>
				<div class="site-people-dialog__media">
					<img class="site-people-dialog__image" data-person-dialog-image alt="">
					<div class="site-people-dialog__fallback" data-person-dialog-fallback>
						<span data-person-dialog-initials></span>
					</div>
				</div>
				<div class="site-people-dialog__content">
					<p class="site-people-dialog__role" data-person-dialog-role></p>
					<h2 id="site-people-dialog-title" class="site-people-dialog__title" data-person-dialog-name></h2>
					<p id="site-people-dialog-bio" class="site-people-dialog__bio" data-person-dialog-bio></p>
					<a class="site-people-dialog__link" data-person-dialog-link href="#">View full profile</a>
				</div>
			</section>
		`;
		document.body.appendChild(dialog);
		return dialog;
	}

	function getPeopleProfileDialog() {
		return document.querySelector('.site-people-dialog') || createPeopleProfileDialog();
	}

	function getFocusableDialogNodes(dialog) {
		return Array.from(
			dialog.querySelectorAll(
				'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])'
			)
		).filter(node => !node.hidden && node.offsetParent !== null);
	}

	function getPeopleProfileDialogState() {
		if (peopleProfileDialogState) {
			return peopleProfileDialogState;
		}
		const dialog = getPeopleProfileDialog();
		const closeButton = dialog.querySelector('[data-person-dialog-close]');
		const backdrop = dialog.querySelector('[data-person-dialog-backdrop]');
		const image = dialog.querySelector('[data-person-dialog-image]');
		const fallback = dialog.querySelector('[data-person-dialog-fallback]');
		const initials = dialog.querySelector('[data-person-dialog-initials]');
		const role = dialog.querySelector('[data-person-dialog-role]');
		const name = dialog.querySelector('[data-person-dialog-name]');
		const bio = dialog.querySelector('[data-person-dialog-bio]');
		const profileLink = dialog.querySelector('[data-person-dialog-link]');
		let activeTrigger = null;

		const closeDialog = () => {
			if (!dialog.classList.contains('is-open')) {
				return;
			}
			dialog.classList.remove('is-open');
			dialog.setAttribute('aria-hidden', 'true');
			document.body.classList.remove('site-dialog-open');
			if (activeTrigger && typeof activeTrigger.focus === 'function') {
				activeTrigger.focus({ preventScroll: true });
			}
			activeTrigger = null;
		};

		const openDialog = card => {
			const personName = card.dataset.personName || '';
			const personTitle = card.dataset.personTitle || '';
			const personBio = card.dataset.personBio || '';
			const personInitials = card.dataset.personInitials || '?';
			const personImage = card.dataset.personImage || '';
			const personProfileUrl = card.dataset.personProfileUrl || '';

			activeTrigger = card;
			name.textContent = personName;
			role.textContent = personTitle;
			role.hidden = !personTitle;
			bio.textContent = personBio;
			bio.hidden = !personBio;
			initials.textContent = personInitials;

			if (personImage) {
				image.src = personImage;
				image.alt = personName ? `${personName} portrait` : 'Profile portrait';
				image.hidden = false;
				fallback.hidden = true;
			} else {
				image.removeAttribute('src');
				image.alt = '';
				image.hidden = true;
				fallback.hidden = false;
			}

			if (personProfileUrl) {
				profileLink.href = personProfileUrl;
				profileLink.hidden = false;
			} else {
				profileLink.removeAttribute('href');
				profileLink.hidden = true;
			}

			dialog.classList.add('is-open');
			dialog.setAttribute('aria-hidden', 'false');
			document.body.classList.add('site-dialog-open');
			closeButton.focus({ preventScroll: true });
		};

		const handleKeydown = event => {
			if (!dialog.classList.contains('is-open')) {
				return;
			}
			if (event.key === 'Escape') {
				event.preventDefault();
				closeDialog();
				return;
			}
			if (event.key !== 'Tab') {
				return;
			}

			const focusable = getFocusableDialogNodes(dialog);
			if (!focusable.length) {
				return;
			}
			const first = focusable[0];
			const last = focusable[focusable.length - 1];
			if (event.shiftKey && document.activeElement === first) {
				event.preventDefault();
				last.focus();
			} else if (!event.shiftKey && document.activeElement === last) {
				event.preventDefault();
				first.focus();
			}
		};

		closeButton.addEventListener('click', closeDialog);
		backdrop.addEventListener('click', closeDialog);
		document.addEventListener('keydown', handleKeydown);

		peopleProfileDialogState = {
			openDialog,
			closeDialog,
		};
		return peopleProfileDialogState;
	}

	function initPeopleProfileDialogs() {
		applyPeoplePhotoFrameStyles();
		if (peopleProfileDialogClickListenerReady) {
			return;
		}
		peopleProfileDialogClickListenerReady = true;
		document.addEventListener('click', event => {
			const trigger = event.target?.closest?.('[data-person-card], [data-person-card-trigger]');
			const card = trigger?.matches?.('[data-person-card]')
				? trigger
				: trigger?.closest?.('[data-person-card]');
			if (!card) {
				return;
			}
			event.preventDefault();
			getPeopleProfileDialogState().openDialog(card);
		});
	}

	window.IfitwalaPeopleProfiles = {
		applyPhotoFrameStyles: applyPeoplePhotoFrameStyles,
		init: initPeopleProfileDialogs,
		open(card) {
			if (!card) {
				return;
			}
			getPeopleProfileDialogState().openDialog(card);
		},
	};

	onReady(initPeopleProfileDialogs);
})();
