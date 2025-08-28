// ifitwala_ed/public/js/portal/student_logs.js
// Copyright (c) 2025
// Purpose: Student Logs portal page logic (list, load more, modal, mark-as-read)

// ---- SHIM: make this file work even if Frappe globals aren't ready yet ----
(function () {
	if (window.frappe && typeof window.__ === 'function') return;

	function getCSRF() {
		// Prefer meta tag from sp_base.html; fall back to window.csrf_token
		const m = document.querySelector('meta[name="csrf-token"]');
		return (m && m.getAttribute('content')) || window.csrf_token || '';
	}

	async function http(method, args = {}, verb = 'POST') {
		const base = '/api/method/' + method;
		const isGET = (verb || 'POST').toUpperCase() === 'GET';

		if (isGET) {
			const qs = new URLSearchParams(args).toString();
			const r = await fetch(qs ? `${base}?${qs}` : base, { method: 'GET', credentials: 'same-origin' });
			const d = await r.json().catch(() => ({}));
			if (!r.ok || d.exc) throw new Error(d._server_messages || d.exc || 'Request failed');
			return { message: d.message ?? d };
		} else {
			const r = await fetch(base, {
				method: 'POST',
				credentials: 'same-origin',
				headers: {
					'Content-Type': 'application/json',
					'X-Frappe-CSRF-Token': getCSRF()
				},
				body: JSON.stringify(args)
			});
			const d = await r.json().catch(() => ({}));
			if (!r.ok || d.exc) throw new Error(d._server_messages || d.exc || 'Request failed');
			return { message: d.message ?? d };
		}
	}

	window.frappe = window.frappe || {
		call: ({ method, args, type }) => http(method, args, type || 'POST'),
		utils: {
			escape_html: s =>
				String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))
		},
		datetime: {
			str_to_user: s => s
		},
		msgprint: ({ title, message, indicator }) => {
			console[(indicator === 'red' ? 'error' : 'warn')](title || 'Notice', message || '');
		}
	};

	if (typeof window.__ !== 'function') {
		window.__ = s => s;
	}
})();

// ----------------------------------------------------------------------------
// Student Logs page
// ----------------------------------------------------------------------------
(function () {
	'use strict';

	// Namespace
	window.ifitwala = window.ifitwala || {};
	ifitwala.portal = ifitwala.portal || {};

	// Public API
	ifitwala.portal.studentLogs = { init };

	// State
	let root, listEl, loadBtn, spinner, modalEl, modal;
	let offset = 0;
	let pageLen = 20;
	let loading = false;

	function init() {
		root = document.getElementById('student-logs-root');
		if (!root || root.dataset.initialized === '1') return;
		root.dataset.initialized = '1';

		listEl = document.getElementById('log-list');
		loadBtn = document.getElementById('load-more');
		spinner = document.getElementById('load-spinner');
		modalEl = document.getElementById('logModal');

		pageLen = Number(root.getAttribute('data-page-length') || '20') || 20;
		offset = listEl ? listEl.querySelectorAll('.student-log-row').length : 0;

		listEl?.querySelectorAll('.student-log-row').forEach(el => {
			el.addEventListener('click', () => openDetail(el.dataset.logName, el));
		});

		loadBtn?.addEventListener('click', fetchMore);

		if (offset < pageLen) {
			loadBtn?.classList.add('d-none');
		}
	}

	function ensureModal() {
		if (!modal) {
			if (!window.bootstrap?.Modal) {
				console.warn('Bootstrap JS not available; modal will not open.');
				return null;
			}
			modal = new bootstrap.Modal(modalEl);
		}
		return modal;
	}

	function setLoading(state) {
		loading = state;
		if (loadBtn) loadBtn.disabled = state;
		if (spinner) spinner.classList.toggle('d-none', !state);
	}

	async function fetchMore() {
		if (loading) return;
		setLoading(true);
		try {
			const r = await frappe.call({
				method: 'ifitwala_ed.ifitwala_ed.api_portal.student_logs_get',
				args: { start: offset, page_length: pageLen },
				type: 'POST'
			});
			const payload = r && r.message ? r.message : { rows: [], unread: [] };
			const rows = payload.rows || [];
			const unread = new Set(payload.unread || []); // present if API returns it

			if (!rows.length) {
				loadBtn?.classList.add('d-none');
				return;
			}

			rows.forEach(row => addRow(row, unread.has(row.name)));
			offset += rows.length;
		} catch (e) {
			console.error(e);
			frappe.msgprint({
				title: __('Error'),
				message: __('Could not load more logs.'),
				indicator: 'red'
			});
		} finally {
			setLoading(false);
		}
	}

	function addRow(row, isUnread) {
		if (!listEl) return;

		const a = document.createElement('a');
		a.href = 'javascript:void(0)';
		a.className = 'list-group-item list-group-item-action d-flex flex-column gap-1 student-log-row';
		a.dataset.logName = row.name;

		const rightBadge = row.follow_up_status
			? `<span class="badge text-bg-secondary ms-auto">${frappe.utils.escape_html(row.follow_up_status)}</span>`
			: '';

		const top = `
			<div class="d-flex w-100 align-items-center">
				<span class="me-2 text-secondary small">${frappe.datetime.str_to_user(row.date)}</span>
				${row.time ? `<span class="me-2 text-secondary small">${row.time}</span>` : ''}
				<strong class="me-2">${frappe.utils.escape_html(row.log_type || '')}</strong>
				${rightBadge}
			</div>`;

		const bits = [`${__('Author')}: ${frappe.utils.escape_html(row.author_name || '-')}`];
		if (row.program) bits.push(`• ${__('Program')}: ${frappe.utils.escape_html(row.program)}`);
		if (row.academic_year) bits.push(`• ${__('Year')}: ${frappe.utils.escape_html(row.academic_year)}`);

		const newPill = isUnread ? `<span class="badge rounded-pill text-bg-primary ms-auto" data-new-pill>NEW</span>` : '';
		const bottom = `
			<div class="d-flex w-100 align-items-center text-muted small">
				<span class="me-2">${bits.join(' ')}</span>
				${newPill}
			</div>`;

		a.innerHTML = top + bottom;
		a.addEventListener('click', () => openDetail(row.name, a));
		listEl.appendChild(a);
	}

	async function openDetail(name, rowEl) {
		if (!name) return;
		try {
			const r = await frappe.call({
				method: 'ifitwala_ed.ifitwala_ed.api_portal.student_log_detail_mark_read',
				args: { name },
				type: 'POST'
			});
			const d = r && r.message ? r.message : {};

			const meta = [];
			if (d.date) meta.push(`${__('Date')}: ${frappe.datetime.str_to_user(d.date)}`);
			if (d.time) meta.push(`${__('Time')}: ${d.time}`);
			if (d.author_name) meta.push(`${__('Author')}: ${d.author_name}`);
			if (d.log_type) meta.push(`${__('Type')}: ${d.log_type}`);
			if (d.program) meta.push(`${__('Program')}: ${d.program}`);
			if (d.academic_year) meta.push(`${__('Year')}: ${d.academic_year}`);
			const metaEl = document.getElementById('modal-meta');
			if (metaEl) metaEl.textContent = meta.join(' • ');

			const badges = document.getElementById('modal-badges');
			if (badges) {
				badges.innerHTML = '';
				if (d.follow_up_status) {
					const span = document.createElement('span');
					span.className = 'badge text-bg-secondary';
					span.textContent = d.follow_up_status;
					badges.appendChild(span);
				}
			}

			const bodyEl = document.getElementById('modal-log-html');
			if (bodyEl) bodyEl.innerHTML = d.log_html || '';

			const refEl = document.getElementById('modal-reference');
			if (refEl) {
				if (d.reference_type && d.reference_name) {
					refEl.classList.remove('d-none');
					refEl.innerHTML = `${__('Reference')}: <span class="text-body">${frappe.utils.escape_html(d.reference_type)}</span>
						<span class="mx-1">/</span><span class="text-body">${frappe.utils.escape_html(d.reference_name)}</span>`;
				} else {
					refEl.classList.add('d-none');
					refEl.innerHTML = '';
				}
			}

			const pill = rowEl?.querySelector('[data-new-pill]');
			if (pill) pill.remove();

			const m = ensureModal();
			if (m) m.show();
		} catch (e) {
			console.error(e);
			frappe.msgprint({
				title: __('Error'),
				message: __('Could not load the log details.'),
				indicator: 'red'
			});
		}
	}
})();

