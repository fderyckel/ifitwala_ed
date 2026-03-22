// ifitwala_ed/public/js/organization_media_dialog.js

(() => {
	const LIST_VISIBLE_METHOD =
		'ifitwala_ed.utilities.organization_media.list_visible_media_for_school';
	const LIST_OWNED_METHOD =
		'ifitwala_ed.utilities.organization_media.list_owned_media_for_organization';
	const UPLOAD_MEDIA_METHOD =
		'ifitwala_ed.utilities.governed_uploads.upload_organization_media_asset';
	const UPLOAD_LOGO_METHOD = 'ifitwala_ed.utilities.governed_uploads.upload_organization_logo';

	function escapeHtml(value) {
		return frappe.utils.escape_html(String(value || ''));
	}

	function ensureStyles() {
		if (document.getElementById('iw-organization-media-styles')) return;
		const style = document.createElement('style');
		style.id = 'iw-organization-media-styles';
		style.textContent = `
			.iw-org-media-dialog {
				display: flex;
				flex-direction: column;
				gap: 1rem;
			}
			.iw-org-media-toolbar {
				display: grid;
				gap: 0.75rem;
				grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
				align-items: end;
			}
			.iw-org-media-actions {
				display: flex;
				gap: 0.5rem;
				flex-wrap: wrap;
			}
			.iw-org-media-results {
				display: grid;
				gap: 0.875rem;
				grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
				max-height: 420px;
				overflow: auto;
				padding-right: 0.25rem;
			}
			.iw-org-media-card {
				border: 1px solid var(--border-color, #d1d5db);
				border-radius: 14px;
				overflow: hidden;
				background: var(--fg-color, #fff);
				display: flex;
				flex-direction: column;
				min-height: 280px;
			}
			.iw-org-media-card.is-active {
				box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.18);
				border-color: #2563eb;
			}
			.iw-org-media-thumb {
				background: linear-gradient(135deg, #f8fafc, #e2e8f0);
				aspect-ratio: 16 / 10;
				display: flex;
				align-items: center;
				justify-content: center;
				overflow: hidden;
			}
			.iw-org-media-thumb img {
				width: 100%;
				height: 100%;
				object-fit: cover;
			}
			.iw-org-media-body {
				padding: 0.875rem;
				display: flex;
				flex-direction: column;
				gap: 0.5rem;
				flex: 1 1 auto;
			}
			.iw-org-media-name {
				font-weight: 600;
				line-height: 1.35;
				word-break: break-word;
			}
			.iw-org-media-meta {
				font-size: 0.82rem;
				color: var(--text-muted, #6b7280);
				display: grid;
				gap: 0.25rem;
			}
			.iw-org-media-badges {
				display: flex;
				gap: 0.4rem;
				flex-wrap: wrap;
			}
			.iw-org-media-badge {
				font-size: 0.72rem;
				border-radius: 999px;
				padding: 0.15rem 0.55rem;
				background: #eef2ff;
				color: #3730a3;
			}
			.iw-org-media-card-actions {
				display: flex;
				gap: 0.5rem;
				margin-top: auto;
				flex-wrap: wrap;
			}
			.iw-org-media-empty {
				border: 1px dashed var(--border-color, #d1d5db);
				border-radius: 14px;
				padding: 1rem;
				color: var(--text-muted, #6b7280);
				background: #f8fafc;
			}
		`;
		document.head.appendChild(style);
	}

	function getScopedSchoolArg(scopeValue) {
		return scopeValue && !['__organization__', '__all__'].includes(scopeValue) ? scopeValue : null;
	}

	function buildScopeOptions({
		schoolOptions = [],
		includeAll = false,
		currentSchool = null,
	} = {}) {
		const options = [];
		if (includeAll) {
			options.push({ value: '__all__', label: __('All Media') });
		}
		options.push({ value: '__organization__', label: __('Organization Shared') });
		schoolOptions.forEach(option => {
			options.push({
				value: option.name,
				label:
					currentSchool && option.name === currentSchool
						? __('This School: {0}', [option.label || option.name])
						: option.label || option.name,
			});
		});
		return options;
	}

	function createToolbar({ host, placeholder, scopeOptions }) {
		const root = document.createElement('div');
		root.className = 'iw-org-media-dialog';

		const toolbar = document.createElement('div');
		toolbar.className = 'iw-org-media-toolbar';

		const searchWrap = document.createElement('div');
		const searchLabel = document.createElement('label');
		searchLabel.className = 'control-label';
		searchLabel.textContent = __('Search');
		const searchInput = document.createElement('input');
		searchInput.type = 'text';
		searchInput.className = 'form-control';
		searchInput.placeholder = placeholder || __('Search by file name or scope');
		searchWrap.appendChild(searchLabel);
		searchWrap.appendChild(searchInput);
		toolbar.appendChild(searchWrap);

		const scopeWrap = document.createElement('div');
		const scopeLabel = document.createElement('label');
		scopeLabel.className = 'control-label';
		scopeLabel.textContent = __('Upload Scope');
		const scopeSelect = document.createElement('select');
		scopeSelect.className = 'form-control';
		(scopeOptions || []).forEach(option => {
			const opt = document.createElement('option');
			opt.value = option.value;
			opt.textContent = option.label;
			scopeSelect.appendChild(opt);
		});
		scopeWrap.appendChild(scopeLabel);
		scopeWrap.appendChild(scopeSelect);
		toolbar.appendChild(scopeWrap);

		const actionWrap = document.createElement('div');
		const actionLabel = document.createElement('label');
		actionLabel.className = 'control-label';
		actionLabel.textContent = __('Actions');
		const actions = document.createElement('div');
		actions.className = 'iw-org-media-actions';
		actionWrap.appendChild(actionLabel);
		actionWrap.appendChild(actions);
		toolbar.appendChild(actionWrap);

		const results = document.createElement('div');
		results.className = 'iw-org-media-results';

		root.appendChild(toolbar);
		root.appendChild(results);
		host.innerHTML = '';
		host.appendChild(root);

		return {
			searchInput,
			scopeSelect,
			actions,
			results,
		};
	}

	function renderMediaResults({ container, items, currentValue, onSelect }) {
		container.innerHTML = '';
		if (!Array.isArray(items) || !items.length) {
			const empty = document.createElement('div');
			empty.className = 'iw-org-media-empty';
			empty.textContent = __('No governed media matched the current filter.');
			container.appendChild(empty);
			return;
		}

		items.forEach(item => {
			const card = document.createElement('div');
			card.className = 'iw-org-media-card';
			if (currentValue && item.file_url === currentValue) {
				card.classList.add('is-active');
			}

			const thumb = document.createElement('div');
			thumb.className = 'iw-org-media-thumb';
			if (item.file_url) {
				const image = document.createElement('img');
				image.src = item.file_url;
				image.alt = item.file_name || item.scope_label || __('Organization media');
				thumb.appendChild(image);
			}
			card.appendChild(thumb);

			const body = document.createElement('div');
			body.className = 'iw-org-media-body';
			body.innerHTML = `
				<div class="iw-org-media-name">${escapeHtml(item.file_name || __('Untitled media'))}</div>
				<div class="iw-org-media-badges">
					<span class="iw-org-media-badge">${escapeHtml(item.scope_label || __('Organization Shared'))}</span>
					<span class="iw-org-media-badge">${escapeHtml(item.organization_label || item.organization || '')}</span>
				</div>
				<div class="iw-org-media-meta">
					<div>${escapeHtml(item.slot || '')}</div>
					<div>${escapeHtml(item.file_url || '')}</div>
				</div>
			`;

			const actions = document.createElement('div');
			actions.className = 'iw-org-media-card-actions';

			if (typeof onSelect === 'function') {
				const useButton = document.createElement('button');
				useButton.type = 'button';
				useButton.className = 'btn btn-sm btn-primary';
				useButton.textContent = __('Use Image');
				useButton.addEventListener('click', () => onSelect(item));
				actions.appendChild(useButton);
			}

			const previewButton = document.createElement('a');
			previewButton.className = 'btn btn-sm btn-default';
			previewButton.href = item.file_url || '#';
			previewButton.target = '_blank';
			previewButton.rel = 'noopener noreferrer';
			previewButton.textContent = __('Preview');
			actions.appendChild(previewButton);

			body.appendChild(actions);
			card.appendChild(body);
			container.appendChild(card);
		});
	}

	function openFileUploader({ method, args, onSuccess, onError }) {
		new frappe.ui.FileUploader({
			method,
			args,
			is_private: 0,
			disable_private: true,
			allow_multiple: false,
			on_success(fileDoc) {
				const payload =
					fileDoc?.message ||
					(Array.isArray(fileDoc) ? fileDoc[0] : fileDoc) ||
					(typeof fileDoc === 'string' ? { file_url: fileDoc } : null);
				if (typeof onSuccess === 'function') {
					onSuccess(payload || {});
				}
			},
			on_error() {
				if (typeof onError === 'function') {
					onError();
					return;
				}
				frappe.msgprint(__('Upload failed. Please try again.'));
			},
		});
	}

	async function fetchVisibleForSchool({ school, query }) {
		const res = await frappe.call({
			method: LIST_VISIBLE_METHOD,
			args: { school, query, limit: 100 },
		});
		return res && res.message ? res.message : { organization: null, items: [] };
	}

	async function fetchOwnedForOrganization({ organization, school, query }) {
		const res = await frappe.call({
			method: LIST_OWNED_METHOD,
			args: { organization, school, query, limit: 100 },
		});
		return res && res.message ? res.message : { organization, items: [], schools: [] };
	}

	function bindSearchReload({ input, reload }) {
		let timer = null;
		input.addEventListener('input', () => {
			if (timer) {
				window.clearTimeout(timer);
			}
			timer = window.setTimeout(() => {
				reload();
			}, 180);
		});
	}

	function openPicker({ school, currentValue = '', title = null, onSelect = null }) {
		if (!school) {
			frappe.msgprint(__('A School context is required for organization media picking.'));
			return null;
		}
		ensureStyles();

		const dialog = new frappe.ui.Dialog({
			title: title || __('Choose from Organization Media'),
			fields: [{ fieldname: 'media_ui', fieldtype: 'HTML' }],
		});
		dialog.set_primary_action(__('Close'), () => dialog.hide());

		const { searchInput, scopeSelect, actions, results } = createToolbar({
			host: dialog.get_field('media_ui').$wrapper.get(0),
			scopeOptions: buildScopeOptions({
				schoolOptions: [{ name: school, label: school }],
				currentSchool: school,
			}),
		});

		let lastOrganization = null;
		const load = async () => {
			const payload = await fetchVisibleForSchool({
				school,
				query: searchInput.value || '',
			});
			lastOrganization = payload.organization || lastOrganization;
			renderMediaResults({
				container: results,
				items: payload.items || [],
				currentValue,
				onSelect: item => {
					if (typeof onSelect === 'function') {
						onSelect(item);
					}
					dialog.hide();
				},
			});
		};

		const uploadCurrentScope = () => {
			const scopeValue = scopeSelect.value || school;
			const scopedSchool = getScopedSchoolArg(scopeValue);
			openFileUploader({
				method: UPLOAD_MEDIA_METHOD,
				args: {
					school,
					scope: scopedSchool ? 'school' : 'organization',
					organization: scopedSchool ? null : lastOrganization || null,
				},
				onSuccess(payload) {
					if (typeof onSelect === 'function' && payload.file_url) {
						onSelect(payload);
					}
					dialog.hide();
				},
			});
		};

		const uploadButton = document.createElement('button');
		uploadButton.type = 'button';
		uploadButton.className = 'btn btn-primary';
		uploadButton.textContent = __('Upload New Image');
		uploadButton.addEventListener('click', uploadCurrentScope);
		actions.appendChild(uploadButton);

		const manageButton = document.createElement('button');
		manageButton.type = 'button';
		manageButton.className = 'btn btn-default';
		manageButton.textContent = __('Manage Media');
		manageButton.addEventListener('click', () => {
			if (!lastOrganization) {
				frappe.msgprint(__('Wait for the media list to load before opening the manager.'));
				return;
			}
			openManager({
				organization: lastOrganization,
				school,
				title: __('Organization Media'),
				onSelect(item) {
					if (typeof onSelect === 'function') {
						onSelect(item);
					}
					dialog.hide();
				},
			});
		});
		actions.appendChild(manageButton);

		bindSearchReload({ input: searchInput, reload: load });
		dialog.show();
		load();
		return dialog;
	}

	function openManager({
		frm = null,
		organization,
		school = null,
		title = null,
		onSelect = null,
	}) {
		if (!organization) {
			frappe.msgprint(__('An Organization is required to manage organization media.'));
			return null;
		}
		ensureStyles();

		const dialog = new frappe.ui.Dialog({
			title: title || __('Organization Media'),
			fields: [{ fieldname: 'media_ui', fieldtype: 'HTML' }],
		});
		dialog.set_primary_action(__('Close'), () => dialog.hide());

		const { searchInput, scopeSelect, actions, results } = createToolbar({
			host: dialog.get_field('media_ui').$wrapper.get(0),
			scopeOptions: buildScopeOptions({ includeAll: true }),
		});

		let schoolOptions = [];
		const preferredScope = school || '__all__';
		const setScopeOptions = () => {
			const currentValue = scopeSelect.value;
			const options = buildScopeOptions({ includeAll: true, schoolOptions });
			scopeSelect.innerHTML = '';
			options.forEach(option => {
				const opt = document.createElement('option');
				opt.value = option.value;
				opt.textContent = option.label;
				scopeSelect.appendChild(opt);
			});
			scopeSelect.value = options.some(option => option.value === currentValue)
				? currentValue
				: options.some(option => option.value === preferredScope)
					? preferredScope
					: '__all__';
		};

		const load = async () => {
			const scopeValue = scopeSelect.value || '__all__';
			const payload = await fetchOwnedForOrganization({
				organization,
				school: scopeValue === '__all__' || scopeValue === '__organization__' ? null : scopeValue,
				query: searchInput.value || '',
			});
			schoolOptions = payload.schools || [];
			setScopeOptions();
			let items = payload.items || [];
			if (scopeValue === '__organization__') {
				items = items.filter(item => !item.school);
			}
			renderMediaResults({
				container: results,
				items,
				currentValue: '',
				onSelect,
			});
		};

		const uploadImage = () => {
			const scopeValue = scopeSelect.value || '__organization__';
			const scopedSchool = getScopedSchoolArg(scopeValue);
			openFileUploader({
				method: UPLOAD_MEDIA_METHOD,
				args: {
					organization,
					school: scopedSchool,
					scope: scopedSchool ? 'school' : 'organization',
				},
				onSuccess() {
					load();
				},
			});
		};

		const uploadLogo = () => {
			openFileUploader({
				method: UPLOAD_LOGO_METHOD,
				args: { organization },
				onSuccess(payload) {
					if (frm && payload.file_url) {
						frm.set_value('organization_logo', payload.file_url);
						frm.set_value('organization_logo_file', payload.file);
						const reload = frm.reload_doc();
						if (reload && reload.then) {
							reload.then(() => frm.refresh_field('organization_logo'));
						}
					}
					load();
				},
			});
		};

		const uploadButton = document.createElement('button');
		uploadButton.type = 'button';
		uploadButton.className = 'btn btn-primary';
		uploadButton.textContent = __('Upload Image');
		uploadButton.addEventListener('click', uploadImage);
		actions.appendChild(uploadButton);

		const logoButton = document.createElement('button');
		logoButton.type = 'button';
		logoButton.className = 'btn btn-default';
		logoButton.textContent = __('Upload Organization Logo');
		logoButton.addEventListener('click', uploadLogo);
		actions.appendChild(logoButton);

		bindSearchReload({ input: searchInput, reload: load });
		scopeSelect.addEventListener('change', load);
		dialog.show();
		load();
		return dialog;
	}

	window.ifitwalaEd = window.ifitwalaEd || {};
	window.ifitwalaEd.organizationMedia = {
		openPicker,
		openManager,
	};
})();
