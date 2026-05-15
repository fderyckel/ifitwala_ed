// ifitwala_ed/public/js/admissions_webform_shell.js

(function () {
	'use strict';

	var APPLY_PREFIX = '/apply/';
	var INQUIRY_ROUTE_PREFIX = '/apply/inquiry';
	var INQUIRY_ORGANIZATION_STORAGE_KEY = 'ifitwala:inquiry:selected-organization';
	var INQUIRY_CONTEXT_STORAGE_KEY = 'ifitwala:inquiry:selected-context';
	var INQUIRY_ACKNOWLEDGEMENT_METHOD =
		'ifitwala_ed.api.inquiry.get_inquiry_acknowledgement_context';
	var INQUIRY_SUCCESS_TITLE = 'Inquiry received';
	var INQUIRY_SUCCESS_MESSAGE_DEFAULT =
		'Your message has been received. A member of our team will get back to you soon.';
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

	function isInquiryRoute() {
		var pathname = window.location.pathname || '';
		return pathname.indexOf(INQUIRY_ROUTE_PREFIX) === 0;
	}

	function getInquiryFieldValue(fieldname) {
		if (!fieldname) {
			return '';
		}
		var selectorFieldname = String(fieldname).replace(/"/g, '');
		var input = document.querySelector(
			'.web-form [data-fieldname="' +
				selectorFieldname +
				'"] input, ' +
				'.web-form [data-fieldname="' +
				selectorFieldname +
				'"] select, ' +
				'.web-form [data-fieldname="' +
				selectorFieldname +
				'"] textarea, ' +
				'.web-form input[name="' +
				selectorFieldname +
				'"], ' +
				'.web-form select[name="' +
				selectorFieldname +
				'"], ' +
				'.web-form textarea[name="' +
				selectorFieldname +
				'"]'
		);

		if (!input) {
			return '';
		}
		return (input.value || '').trim();
	}

	function getInquiryOrganizationValue() {
		return getInquiryFieldValue('organization');
	}

	function getInquiryContextValues() {
		return {
			organization: getInquiryFieldValue('organization'),
			school: getInquiryFieldValue('school'),
			type_of_inquiry: getInquiryFieldValue('type_of_inquiry'),
		};
	}

	function saveInquiryOrganizationValue(value) {
		if (!value) {
			return;
		}
		try {
			window.sessionStorage.setItem(INQUIRY_ORGANIZATION_STORAGE_KEY, value);
		} catch (error) {
			// Ignore browser storage errors and keep the default success copy.
		}
	}

	function clearInquiryOrganizationValue() {
		try {
			window.sessionStorage.removeItem(INQUIRY_ORGANIZATION_STORAGE_KEY);
			window.sessionStorage.removeItem(INQUIRY_CONTEXT_STORAGE_KEY);
		} catch (error) {
			// Ignore browser storage errors and keep runtime behavior unchanged.
		}
	}

	function readInquiryOrganizationValue() {
		try {
			return (window.sessionStorage.getItem(INQUIRY_ORGANIZATION_STORAGE_KEY) || '').trim();
		} catch (error) {
			return '';
		}
	}

	function saveInquiryContext(context) {
		context = context || {};
		if (!context.organization && !context.school && !context.type_of_inquiry) {
			clearInquiryOrganizationValue();
			return;
		}
		if (context.organization) {
			saveInquiryOrganizationValue(context.organization);
		}
		try {
			window.sessionStorage.setItem(INQUIRY_CONTEXT_STORAGE_KEY, JSON.stringify(context));
		} catch (error) {
			// Ignore browser storage errors and keep the default success copy.
		}
	}

	function readInquiryContext() {
		var fallbackOrganization = readInquiryOrganizationValue();
		try {
			var raw = window.sessionStorage.getItem(INQUIRY_CONTEXT_STORAGE_KEY) || '';
			var parsed = raw ? JSON.parse(raw) : {};
			return {
				organization: (parsed.organization || fallbackOrganization || '').trim(),
				school: (parsed.school || '').trim(),
				type_of_inquiry: (parsed.type_of_inquiry || '').trim(),
			};
		} catch (error) {
			return {
				organization: fallbackOrganization,
				school: '',
				type_of_inquiry: '',
			};
		}
	}

	function normalizeInquiryContext(contextOverride) {
		var formContext = getInquiryContextValues();
		var storedContext = readInquiryContext();
		var override = {};
		if (typeof contextOverride === 'string') {
			override.organization = contextOverride.trim();
		} else if (contextOverride && typeof contextOverride === 'object') {
			override = contextOverride;
		}
		return {
			organization: (
				override.organization ||
				formContext.organization ||
				storedContext.organization ||
				''
			).trim(),
			school: (override.school || formContext.school || storedContext.school || '').trim(),
			type_of_inquiry: (
				override.type_of_inquiry ||
				formContext.type_of_inquiry ||
				storedContext.type_of_inquiry ||
				''
			).trim(),
		};
	}

	function buildInquirySuccessMessage(context) {
		context = context || {};
		var school = (context.school || '').trim();
		var organization = (context.organization || '').trim();
		if (!school && !organization) {
			return INQUIRY_SUCCESS_MESSAGE_DEFAULT;
		}

		if (school) {
			return (
				'Your message has been received. Someone from ' + school + ' will get back to you soon.'
			);
		}
		return (
			'Your message has been received. Someone from ' +
			organization +
			' will get back to you soon.'
		);
	}

	function clearNode(node) {
		while (node.firstChild) {
			node.removeChild(node.firstChild);
		}
	}

	function buildDefaultAcknowledgementPayload(context) {
		return {
			brand: {
				name: context.school || context.organization || 'Ifitwala',
				logo: '',
			},
			title: INQUIRY_SUCCESS_TITLE,
			message: buildInquirySuccessMessage(context),
			timeline_intro: 'What happens next',
			timeline: [
				{
					label: 'Inquiry received',
					description: 'Your message is now in the admissions inbox.',
				},
				{
					label: 'Admissions review',
					description: 'The team checks the school context and preferred contact channel.',
				},
				{
					label: 'Family follow-up',
					description: 'A staff member replies with the next practical action.',
				},
			],
			footer_note: '',
			ctas: [],
		};
	}

	function getInquiryContextKey(context) {
		context = context || {};
		return [context.organization || '', context.school || '', context.type_of_inquiry || ''].join(
			'|'
		);
	}

	function buildActionLink(className, label, url) {
		var link = createElement('a', className, label);
		link.setAttribute('href', url);
		if (/^https:\/\//.test(url)) {
			link.setAttribute('target', '_blank');
			link.setAttribute('rel', 'noopener');
		}
		return link;
	}

	function renderInquiryAcknowledgement(successNode, payload, context) {
		if (!successNode || !payload) {
			return;
		}

		var title = (payload.title || INQUIRY_SUCCESS_TITLE).trim();
		var message = (payload.message || INQUIRY_SUCCESS_MESSAGE_DEFAULT).trim();
		var contextKey = getInquiryContextKey(context);
		clearNode(successNode);
		successNode.classList.add('if-inquiry-confirmation-page');
		successNode.setAttribute('data-if-inquiry-owned', '1');
		successNode.setAttribute('data-if-ack-render-context', contextKey);

		var confirmation = createElement('article', 'if-inquiry-confirmation');
		var hero = createElement('div', 'if-inquiry-confirmation__hero');
		var icon = createElement('span', 'if-inquiry-confirmation__icon');
		icon.setAttribute('aria-hidden', 'true');
		icon.appendChild(createElement('span', 'if-inquiry-confirmation__check'));

		var heroCopy = createElement('div', 'if-inquiry-confirmation__hero-copy');
		var heading = createElement('h1', 'if-inquiry-confirmation__title', title);
		var body = createElement('p', 'if-inquiry-confirmation__message', message);
		heroCopy.appendChild(heading);
		heroCopy.appendChild(body);
		hero.appendChild(icon);
		hero.appendChild(heroCopy);
		confirmation.appendChild(hero);

		var brand = payload.brand || {};
		if (brand.name || brand.logo) {
			var brandRow = createElement('div', 'if-inquiry-confirmation__brand');
			if (brand.logo) {
				var logo = createElement('img', 'if-inquiry-confirmation__logo');
				logo.setAttribute('src', brand.logo);
				logo.setAttribute('alt', '');
				brandRow.appendChild(logo);
			}
			if (brand.name) {
				var brandText = createElement('div', 'if-inquiry-confirmation__brand-copy');
				brandText.appendChild(createElement('span', 'if-inquiry-confirmation__eyebrow', 'School'));
				brandText.appendChild(
					createElement('strong', 'if-inquiry-confirmation__brand-name', brand.name)
				);
				brandRow.appendChild(brandText);
			}
			confirmation.appendChild(brandRow);
		}

		var timeline = Array.isArray(payload.timeline) ? payload.timeline : [];
		if (timeline.length) {
			var timelineSection = createElement('section', 'if-inquiry-confirmation__timeline-section');
			var timelineTitle = createElement('h2', 'if-inquiry-confirmation__section-title');
			timelineTitle.textContent = payload.timeline_intro || 'What happens next';
			var timelineList = createElement('div', 'if-inquiry-confirmation__timeline');
			for (var i = 0; i < timeline.length; i++) {
				var item = timeline[i] || {};
				var itemNode = createElement('div', 'if-inquiry-confirmation__step');
				itemNode.appendChild(
					createElement('span', 'if-inquiry-confirmation__step-number', String(i + 1))
				);
				var itemBody = createElement('div', 'if-inquiry-confirmation__step-body');
				itemBody.appendChild(
					createElement('strong', 'if-inquiry-confirmation__step-label', item.label || 'Next step')
				);
				if (item.description) {
					itemBody.appendChild(
						createElement('p', 'if-inquiry-confirmation__step-description', item.description)
					);
				}
				itemNode.appendChild(itemBody);
				timelineList.appendChild(itemNode);
			}
			timelineSection.appendChild(timelineTitle);
			timelineSection.appendChild(timelineList);
			confirmation.appendChild(timelineSection);
		}

		var ctas = Array.isArray(payload.ctas) ? payload.ctas : [];
		var ctaRow = createElement('div', 'if-inquiry-confirmation__actions');
		if (ctas.length) {
			for (var j = 0; j < ctas.length; j++) {
				var cta = ctas[j] || {};
				if (!cta.url || !cta.label) {
					continue;
				}
				ctaRow.appendChild(
					buildActionLink(
						'if-inquiry-confirmation__action if-inquiry-confirmation__action--' +
							(cta.kind || 'link'),
						cta.label,
						cta.url
					)
				);
			}
		}
		ctaRow.appendChild(
			buildActionLink(
				'if-inquiry-confirmation__action if-inquiry-confirmation__action--secondary',
				'Submit another inquiry',
				INQUIRY_ROUTE_PREFIX
			)
		);
		confirmation.appendChild(ctaRow);

		if (payload.footer_note) {
			confirmation.appendChild(
				createElement('p', 'if-inquiry-confirmation__footer-note', payload.footer_note)
			);
		}

		successNode.appendChild(confirmation);
	}

	function loadInquiryAcknowledgementContext(successNode, context) {
		if (!successNode || !window.frappe || typeof window.frappe.call !== 'function') {
			return;
		}

		var contextKey = getInquiryContextKey(context);
		if (successNode.getAttribute('data-if-ack-load-context') === contextKey) {
			return;
		}
		successNode.setAttribute('data-if-ack-load-context', contextKey);

		window.frappe.call({
			method: INQUIRY_ACKNOWLEDGEMENT_METHOD,
			args: context,
			callback: function (response) {
				if (response && response.message) {
					renderInquiryAcknowledgement(successNode, response.message, context);
				}
			},
		});
	}

	function applyInquirySuccessCopy(contextOverride) {
		if (!isInquiryRoute()) {
			return;
		}

		var successNode = document.querySelector('.success-page');
		if (!successNode) {
			return;
		}

		var context = normalizeInquiryContext(contextOverride);
		saveInquiryContext(context);
		if (
			successNode.getAttribute('data-if-inquiry-owned') !== '1' ||
			successNode.getAttribute('data-if-ack-render-context') !== getInquiryContextKey(context)
		) {
			renderInquiryAcknowledgement(
				successNode,
				buildDefaultAcknowledgementPayload(context),
				context
			);
		}
		loadInquiryAcknowledgementContext(successNode, context);
	}

	function bindInquirySubmitSuccessCopy() {
		if (!isInquiryRoute()) {
			return;
		}

		var formNode = document.querySelector('.web-form');
		if (!formNode || formNode.getAttribute('data-if-inquiry-submit-bound') === '1') {
			return;
		}

		formNode.setAttribute('data-if-inquiry-submit-bound', '1');
		formNode.addEventListener('submit', function () {
			var context = getInquiryContextValues();
			saveInquiryContext(context);
			applyInquirySuccessCopy(context);
		});
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

		nav.appendChild(inquiryLink);
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
		var selectNodes = document.querySelectorAll('.web-form select');

		for (var i = 0; i < selectNodes.length; i++) {
			var select = selectNodes[i];
			var rawSize = select.getAttribute('size');
			var parsedSize = parseInt(rawSize || '0', 10);
			var allowMultiple = select.classList.contains('if-webform-allow-multiple');

			select.classList.add('if-webform-select');
			select.classList.add('if-webform-single-select');

			if (!allowMultiple && !Number.isNaN(parsedSize) && parsedSize > 1) {
				select.setAttribute('size', '1');
			}
			if (!allowMultiple) {
				select.removeAttribute('multiple');
				select.setAttribute('size', '1');
			}
			select.style.overflowY = 'hidden';
		}
	}

	function normalizeActionButtons() {
		var buttonNodes = document.querySelectorAll('.web-form-actions button, .web-form-actions a');

		for (var i = 0; i < buttonNodes.length; i++) {
			var button = buttonNodes[i];
			var label = (button.textContent || '').trim().toLowerCase();
			var isPrimary = button.getAttribute('type') === 'submit' || label === 'submit';
			var tokens = (button.className || '').split(/\s+/);
			var keep = [];
			for (var j = 0; j < tokens.length; j++) {
				var token = tokens[j];
				if (!token || token === 'btn' || token.indexOf('btn-') === 0) {
					continue;
				}
				keep.push(token);
			}
			button.className = keep.join(' ');
			button.classList.add('if-wf-btn');
			button.classList.toggle('if-wf-btn--primary', isPrimary);
			button.classList.toggle('if-wf-btn--secondary', !isPrimary);
		}
	}

	function isTechnicalFieldToken(text) {
		return /^[a-z][a-z0-9_]*$/.test(text) && text.indexOf('_') !== -1;
	}

	function collectRenderedFieldTokens() {
		var tokens = Object.create(null);
		var fieldHolders = document.querySelectorAll('.web-form [data-fieldname]');
		for (var i = 0; i < fieldHolders.length; i++) {
			var holderToken = (fieldHolders[i].getAttribute('data-fieldname') || '')
				.trim()
				.toLowerCase();
			if (holderToken) {
				tokens[holderToken] = true;
			}
		}

		var namedFields = document.querySelectorAll(
			'.web-form input[name], .web-form select[name], .web-form textarea[name]'
		);
		for (var j = 0; j < namedFields.length; j++) {
			var namedToken = (namedFields[j].getAttribute('name') || '').trim().toLowerCase();
			if (namedToken) {
				tokens[namedToken] = true;
			}
		}

		return tokens;
	}

	function hideRedundantFieldnameHints() {
		var fieldnameNodes = document.querySelectorAll('.web-form .fieldname, .web-form .field-name');
		var fieldTokens = collectRenderedFieldTokens();

		for (var i = 0; i < fieldnameNodes.length; i++) {
			fieldnameNodes[i].classList.add('if-webform-hidden-meta');
		}

		var helperNodes = document.querySelectorAll(
			'.web-form .form-group .help-box, .web-form .form-group .text-muted, .web-form .form-group .small'
		);
		for (var j = 0; j < helperNodes.length; j++) {
			var node = helperNodes[j];
			var text = (node.textContent || '').trim();

			if (isTechnicalFieldToken(text)) {
				node.classList.add('if-webform-hidden-meta');
			}
		}

		var leafNodes = document.querySelectorAll(
			'.web-form .web-form-body p, .web-form .web-form-body span, .web-form .web-form-body div, .web-form .web-form-body small'
		);
		for (var k = 0; k < leafNodes.length; k++) {
			var candidate = leafNodes[k];
			if (!candidate || candidate.children.length > 0) {
				continue;
			}
			if (
				candidate.closest(
					'label, .control-label, .if-wf-btn, [role="listbox"], .awesomplete, select, textarea, input'
				)
			) {
				continue;
			}

			var candidateText = (candidate.textContent || '').trim();
			var normalized = candidateText.toLowerCase();
			if (
				isTechnicalFieldToken(candidateText) ||
				fieldTokens[normalized] ||
				candidateText === '▲' ||
				candidateText === '▼'
			) {
				candidate.classList.add('if-webform-hidden-meta');
			}
		}
	}

	function syncSubmissionState() {
		var formNode = document.querySelector('.web-form');
		var formContainerNode = document.querySelector('.web-form-container');
		var successNode = document.querySelector('.success-page');

		if (!successNode) {
			document.body.classList.remove('if-webform-submitted');
			return;
		}

		if (!formNode && !formContainerNode) {
			document.body.classList.add('if-webform-submitted');
			return;
		}

		var hiddenByClass =
			formNode && (formNode.classList.contains('hide') || formNode.classList.contains('hidden'));
		var hiddenByAttr = formNode && formNode.getAttribute('aria-hidden') === 'true';
		var hiddenByStyle = formNode && window.getComputedStyle(formNode).display === 'none';
		var containerHiddenByClass =
			formContainerNode &&
			(formContainerNode.classList.contains('hide') ||
				formContainerNode.classList.contains('hidden'));
		var containerHiddenByAttr =
			formContainerNode && formContainerNode.getAttribute('aria-hidden') === 'true';
		var containerHiddenByStyle =
			formContainerNode && window.getComputedStyle(formContainerNode).display === 'none';
		var isSubmitted =
			hiddenByClass ||
			hiddenByAttr ||
			hiddenByStyle ||
			containerHiddenByClass ||
			containerHiddenByAttr ||
			containerHiddenByStyle;
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
		normalizeActionButtons();
		hideRedundantFieldnameHints();
		bindInquirySubmitSuccessCopy();
		syncSubmissionState();
		if (document.body.classList.contains('if-webform-submitted')) {
			applyInquirySuccessCopy();
		}

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
