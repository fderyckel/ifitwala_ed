// ifitwala_ed/public/js/admissions_webform_shell.js

;(function () {
	"use strict";

	var APPLY_PREFIX = "/apply/";
	var SHELL_ROOT_ID = "ifitwala-webform-shell-root";
	var SHELL_FOOTER_ID = "ifitwala-webform-shell-footer";
	var SHELL_CSS_ID = "ifitwala-webform-shell-css";
	var SHELL_CSS_HREF = "/assets/ifitwala_ed/css/admissions_webform_shell.css";
	var SHELL_CSS_FALLBACK_HREF = "/assets/ifitwala_ed/public/css/admissions_webform_shell.css";

	function createElement(tag, className, text) {
		var el = document.createElement(tag);
		if (className) {
			el.className = className;
		}
		if (typeof text === "string") {
			el.textContent = text;
		}
		return el;
	}

	function getContextText() {
		var params = new URLSearchParams(window.location.search || "");
		var school = (params.get("school") || "").trim();
		var organization = (params.get("organization") || "").trim();
		var parts = [];

		if (school) {
			parts.push("School: " + school);
		}
		if (organization) {
			parts.push("Organization: " + organization);
		}
		return parts.join(" | ");
	}

	function buildShellHeader() {
		var header = createElement("header", "if-webform-shell-header");
		header.id = SHELL_ROOT_ID;

		var inner = createElement("div", "if-webform-shell-inner");
		var brand = createElement("a", "if-webform-shell-brand", "Ifitwala");
		brand.setAttribute("href", "/");

		var nav = createElement("nav", "if-webform-shell-nav");
		var inquiryLink = createElement("a", "if-webform-shell-link", "Inquiry");
		inquiryLink.setAttribute("href", "/apply/inquiry");
		var roiLink = createElement("a", "if-webform-shell-link", "Registration of Interest");
		roiLink.setAttribute("href", "/apply/registration-of-interest");

		nav.appendChild(inquiryLink);
		nav.appendChild(roiLink);
		inner.appendChild(brand);
		inner.appendChild(nav);
		header.appendChild(inner);

		var contextText = getContextText();
		if (contextText) {
			var contextBadge = createElement("div", "if-webform-shell-context", contextText);
			header.appendChild(contextBadge);
		}

		return header;
	}

	function buildShellFooter() {
		var footer = createElement("footer", "if-webform-shell-footer");
		footer.id = SHELL_FOOTER_ID;
		var text = createElement(
			"p",
			"if-webform-shell-footer-text",
			"Copyright " + new Date().getFullYear() + " Ifitwala. All rights reserved."
		);
		footer.appendChild(text);
		return footer;
	}

	function markFormContainer() {
		var selectors = [
			".web-form-container",
			".web-form-page .page-content",
			".web-form-page .page_content",
			".page_content",
		];

		for (var i = 0; i < selectors.length; i++) {
			var node = document.querySelector(selectors[i]);
			if (node) {
				node.classList.add("if-webform-shell-container");
				return;
			}
		}
	}

	function injectShell() {
		if (!window.location.pathname || window.location.pathname.indexOf(APPLY_PREFIX) !== 0) {
			return;
		}

		if (!document.getElementById(SHELL_CSS_ID)) {
			var cssLink = createElement("link");
			cssLink.id = SHELL_CSS_ID;
			cssLink.rel = "stylesheet";
			cssLink.href = SHELL_CSS_HREF;
			cssLink.onerror = function () {
				if (cssLink.href.indexOf(SHELL_CSS_FALLBACK_HREF) === -1) {
					cssLink.href = SHELL_CSS_FALLBACK_HREF;
				}
			};
			document.head.appendChild(cssLink);
		}

		document.body.classList.add("ifitwala-public-webform");
		markFormContainer();

		if (!document.getElementById(SHELL_ROOT_ID)) {
			var header = buildShellHeader();
			document.body.insertBefore(header, document.body.firstChild);
		}

		if (!document.getElementById(SHELL_FOOTER_ID)) {
			document.body.appendChild(buildShellFooter());
		}
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", injectShell);
	} else {
		injectShell();
	}

	var observer = new MutationObserver(function () {
		injectShell();
	});
	observer.observe(document.documentElement, { childList: true, subtree: true });
})();
