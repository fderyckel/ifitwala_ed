// ifitwala_ed/public/js/admissions_webform_shell.js

(function () {
	'use strict';

	var APPLY_PREFIX = '/apply/';
	var SHELL_ROOT_ID = 'ifitwala-webform-shell-root';
	var SHELL_FOOTER_ID = 'ifitwala-webform-shell-footer';
	var SHELL_CSS_ID = 'ifitwala-webform-shell-css';
	var SHELL_CSS_HREF = '/assets/ifitwala_ed/css/admissions_webform_shell.css';
	var SHELL_CSS_FALLBACK_HREF = '/assets/ifitwala_ed/public/css/admissions_webform_shell.css';

	function createElement(tag, className, text) {
		var el = document.createElement(tag);
		if (className) {
			el.className = className;
		}
		if (typeof text === 'string') {
			el.textContent = text;
		}
		return el;
	}

	function getContextText() {
		var params = new URLSearchParams(window.location.search || '');
		var school = (params.get('school') || '').trim();
		var organization = (params.get('organization') || '').trim();
		var parts = [];

		if (school) {
			parts.push('School: ' + school);
		}
		if (organization) {
			parts.push('Organization: ' + organization);
		}
		return parts.join(' | ');
	}

	function buildShellHeader() {
		var header = createElement('header', 'if-webform-shell-header');
		header.id = SHELL_ROOT_ID;

		var inner = createElement('div', 'if-webform-shell-inner');
		var brand = createElement('a', 'if-webform-shell-brand', 'Ifitwala');
		brand.setAttribute('href', '/');

		var nav = createElement('nav', 'if-webform-shell-nav');
		var inquiryLink = createElement('a', 'if-webform-shell-link', 'Inquiry');
		inquiryLink.setAttribute('href', '/apply/inquiry');
		var roiLink = createElement('a', 'if-webform-shell-link', 'Registration of Interest');
		roiLink.setAttribute('href', '/apply/registration-of-interest');

		nav.appendChild(inquiryLink);
		nav.appendChild(roiLink);
		inner.appendChild(brand);
		inner.appendChild(nav);
		header.appendChild(inner);

		var contextText = getContextText();
		if (contextText) {
			var contextBadge = createElement('div', 'if-webform-shell-context', contextText);
			header.appendChild(contextBadge);
		}

		return header;
	}

	function buildShellFooter() {
		var footer = createElement('footer', 'if-webform-shell-footer');
		footer.id = SHELL_FOOTER_ID;
		var text = createElement(
			'p',
			'if-webform-shell-footer-text',
			'Copyright ' + new Date().getFullYear() + ' Ifitwala. All rights reserved.'
		);
		footer.appendChild(text);
		return footer;
	}

	function markFormContainer() {
		var selectors = [
			'.web-form-container',
			'.web-form-page .page-content',
			'.web-form-page .page_content',
			'.page_content',
		];

		for (var i = 0; i < selectors.length; i++) {
			var node = document.querySelector(selectors[i]);
			if (node) {
				node.classList.add('if-webform-shell-container');
				return;
			}
		}
	}

	function markActiveNavigationLink() {
		var pathname = window.location.pathname || '';
		var links = document.querySelectorAll('.if-webform-shell-link');

		for (var i = 0; i < links.length; i++) {
			var link = links[i];
			var href = (link.getAttribute('href') || '').trim();
			var isActive = false;

			if (href && pathname.indexOf(href) === 0) {
				isActive = true;
			}

			link.classList.toggle('is-active', isActive);
			if (isActive) {
				link.setAttribute('aria-current', 'page');
			} else {
				link.removeAttribute('aria-current');
			}
		}
	}

	function normalizeSelectControls() {
		var selectNodes = document.querySelectorAll('.web-form select:not([multiple])');

		for (var i = 0; i < selectNodes.length; i++) {
			var select = selectNodes[i];
			var rawSize = select.getAttribute('size');
			var parsedSize = parseInt(rawSize || '0', 10);

			if (!Number.isNaN(parsedSize) && parsedSize > 1) {
				select.setAttribute('size', '1');
			}
			select.removeAttribute('multiple');
			select.style.overflowY = 'hidden';
		}
	}

	function hideRedundantFieldnameHints() {
		var fieldnameNodes = document.querySelectorAll('.web-form .fieldname, .web-form .field-name');

		for (var i = 0; i < fieldnameNodes.length; i++) {
			fieldnameNodes[i].classList.add('if-webform-hidden-meta');
		}

		var helperNodes = document.querySelectorAll(
			'.web-form .form-group .help-box, .web-form .form-group .text-muted, .web-form .form-group .small'
		);
		for (var j = 0; j < helperNodes.length; j++) {
			var node = helperNodes[j];
			var text = (node.textContent || '').trim();

			if (/^[a-z][a-z0-9_]*$/.test(text)) {
				node.classList.add('if-webform-hidden-meta');
			}
		}
	}

	function syncSubmissionState() {
		var formNode = document.querySelector('.web-form');
		var successNode = document.querySelector('.success-page');

		if (!successNode) {
			document.body.classList.remove('if-webform-submitted');
			return;
		}

		if (!formNode) {
			document.body.classList.add('if-webform-submitted');
			return;
		}

		var hiddenByClass =
			formNode.classList.contains('hide') || formNode.classList.contains('hidden');
		var hiddenByAttr = formNode.getAttribute('aria-hidden') === 'true';
		var hiddenByStyle = window.getComputedStyle(formNode).display === 'none';
		var isSubmitted = hiddenByClass || hiddenByAttr || hiddenByStyle;
		document.body.classList.toggle('if-webform-submitted', isSubmitted);
	}

	function injectShell() {
		if (!window.location.pathname || window.location.pathname.indexOf(APPLY_PREFIX) !== 0) {
			return;
		}

		if (!document.getElementById(SHELL_CSS_ID)) {
			var cssLink = createElement('link');
			cssLink.id = SHELL_CSS_ID;
			cssLink.rel = 'stylesheet';
			cssLink.href = SHELL_CSS_HREF;
			cssLink.onerror = function () {
				if (cssLink.href.indexOf(SHELL_CSS_FALLBACK_HREF) === -1) {
					cssLink.href = SHELL_CSS_FALLBACK_HREF;
				}
			};
			document.head.appendChild(cssLink);
		}

		document.body.classList.add('ifitwala-public-webform');
		markFormContainer();
		normalizeSelectControls();
		hideRedundantFieldnameHints();
		syncSubmissionState();

		if (!document.getElementById(SHELL_ROOT_ID)) {
			var header = buildShellHeader();
			document.body.insertBefore(header, document.body.firstChild);
		}
		markActiveNavigationLink();

		if (!document.getElementById(SHELL_FOOTER_ID)) {
			document.body.appendChild(buildShellFooter());
		}
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', injectShell);
	} else {
		injectShell();
	}

	var observer = new MutationObserver(function () {
		injectShell();
	});
	observer.observe(document.documentElement, { childList: true, subtree: true });
})();
