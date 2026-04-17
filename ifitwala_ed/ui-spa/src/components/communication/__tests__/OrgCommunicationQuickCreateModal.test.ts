import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const {
	addOrgCommunicationLinkMock,
	createOrgCommunicationQuickMock,
	getOptionsMock,
	removeOrgCommunicationAttachmentMock,
	uploadOrgCommunicationAttachmentMock,
} = vi.hoisted(() => ({
	addOrgCommunicationLinkMock: vi.fn(),
	createOrgCommunicationQuickMock: vi.fn(),
	getOptionsMock: vi.fn(),
	removeOrgCommunicationAttachmentMock: vi.fn(),
	uploadOrgCommunicationAttachmentMock: vi.fn(),
}));

vi.mock('@headlessui/vue', () => {
	const passthrough = (tag = 'div') =>
		defineComponent({
			name: `Stub${tag}`,
			props: ['as', 'show'],
			setup(props, { slots, attrs }) {
				return () => {
					if (props.show === false) return null;
					return h(props.as && props.as !== 'template' ? props.as : tag, attrs, slots.default?.());
				};
			},
		});

	return {
		Dialog: passthrough('div'),
		DialogPanel: passthrough('div'),
		DialogTitle: passthrough('h2'),
		TransitionChild: passthrough('div'),
		TransitionRoot: passthrough('div'),
	};
});

vi.mock('frappe-ui', () => ({
	Button: defineComponent({
		name: 'ButtonStub',
		props: ['disabled', 'loading', 'type', 'appearance'],
		emits: ['click'],
		setup(props, { slots, emit, attrs }) {
			return () =>
				h(
					'button',
					{
						...attrs,
						type: props.type || 'button',
						disabled: props.disabled,
						'data-appearance': props.appearance,
						onClick: (event: MouseEvent) => emit('click', event),
					},
					slots.default?.()
				);
		},
	}),
	FormControl: defineComponent({
		name: 'FormControlStub',
		props: [
			'modelValue',
			'type',
			'options',
			'disabled',
			'rows',
			'placeholder',
			'optionLabel',
			'optionValue',
		],
		emits: ['update:modelValue'],
		setup(props, { emit }) {
			const resolveOption = (option: unknown) => {
				if (typeof option === 'string') return { label: option, value: option };
				if (option && typeof option === 'object') {
					const row = option as Record<string, unknown>;
					const labelKey = typeof props.optionLabel === 'string' ? props.optionLabel : 'label';
					const valueKey = typeof props.optionValue === 'string' ? props.optionValue : 'value';
					return {
						label: String(row[labelKey] ?? row.label ?? row.value ?? ''),
						value: String(row[valueKey] ?? row.value ?? row.label ?? ''),
					};
				}
				return { label: '', value: '' };
			};

			return () => {
				if (props.type === 'select') {
					return h(
						'select',
						{
							value: props.modelValue ?? '',
							disabled: props.disabled,
							onChange: (event: Event) =>
								emit('update:modelValue', (event.target as HTMLSelectElement).value),
						},
						(props.options || []).map(option => {
							const resolved = resolveOption(option);
							return h('option', { value: resolved.value }, resolved.label);
						})
					);
				}

				if (props.type === 'textarea') {
					return h('textarea', {
						value: props.modelValue ?? '',
						rows: props.rows,
						placeholder: props.placeholder,
						disabled: props.disabled,
						onInput: (event: Event) =>
							emit('update:modelValue', (event.target as HTMLTextAreaElement).value),
					});
				}

				return h('input', {
					type: props.type || 'text',
					value: props.modelValue ?? '',
					placeholder: props.placeholder,
					disabled: props.disabled,
					onInput: (event: Event) =>
						emit('update:modelValue', (event.target as HTMLInputElement).value),
				});
			};
		},
	}),
	FeatherIcon: defineComponent({
		name: 'FeatherIconStub',
		setup() {
			return () => h('span');
		},
	}),
	Spinner: defineComponent({
		name: 'SpinnerStub',
		setup() {
			return () => h('span');
		},
	}),
	TextEditor: defineComponent({
		name: 'TextEditorStub',
		props: ['content', 'placeholder', 'editable', 'fixedMenu', 'editorClass'],
		emits: ['change'],
		setup(props, { emit }) {
			return () =>
				h('div', { class: 'text-editor-stub' }, [
					h(
						'div',
						{ class: 'text-editor-stub__toolbar' },
						(Array.isArray(props.fixedMenu) ? props.fixedMenu : [])
							.flatMap(button => (Array.isArray(button) ? button.slice(0, 1) : [button]))
							.filter(button => button !== 'Separator')
							.slice(0, 4)
							.map(button =>
								h(
									'button',
									{
										title: String(button),
										'data-editor-toolbar-button': String(button),
									},
									String(button)
								)
							)
					),
					h('textarea', {
						value: props.content ?? '',
						placeholder: props.placeholder,
						disabled: props.editable === false,
						'data-text-editor': 'true',
						class: props.editorClass,
						onInput: (event: Event) =>
							emit('change', (event.target as HTMLTextAreaElement).value),
					}),
				]);
		},
	}),
}));

vi.mock('@/lib/services/orgCommunicationQuickCreateService', () => ({
	addOrgCommunicationLink: addOrgCommunicationLinkMock,
	createOrgCommunicationQuick: createOrgCommunicationQuickMock,
	getOrgCommunicationQuickCreateOptions: getOptionsMock,
	removeOrgCommunicationAttachment: removeOrgCommunicationAttachmentMock,
	uploadOrgCommunicationAttachment: uploadOrgCommunicationAttachmentMock,
}));

import OrgCommunicationQuickCreateModal from '@/components/communication/OrgCommunicationQuickCreateModal.vue';

const cleanupFns: Array<() => void> = [];

const quickCreateOptions = {
	context: {
		default_school: 'SCH-1',
		default_organization: 'ORG-1',
		allowed_schools: ['SCH-1'],
		allowed_organizations: ['ORG-1'],
		is_privileged: false,
		can_select_school: true,
		lock_to_default_school: false,
	},
	defaults: {
		communication_type: 'Information',
		status: 'Draft',
		priority: 'Normal',
		portal_surface: 'Desk',
		interaction_mode: 'None',
		allow_private_notes: 0,
		allow_public_thread: 0,
	},
	fields: {
		communication_types: ['Information'],
		statuses: ['Draft', 'Scheduled', 'Published'],
		priorities: ['Normal'],
		portal_surfaces: ['Desk'],
		interaction_modes: ['None'],
		audience_target_modes: ['School Scope', 'Team', 'Student Group'],
	},
	recipient_rules: {
		'School Scope': {
			allowed_fields: ['to_students', 'to_guardians'],
			allowed_labels: ['Students', 'Guardians'],
			default_fields: [],
		},
		Team: {
			allowed_fields: ['to_staff'],
			allowed_labels: ['Staff'],
			default_fields: ['to_staff'],
		},
		'Student Group': {
			allowed_fields: ['to_students', 'to_guardians'],
			allowed_labels: ['Students', 'Guardians'],
			default_fields: ['to_students', 'to_guardians'],
		},
	},
	references: {
		organizations: [{ name: 'ORG-1', organization_name: 'Root Org', abbr: 'RO' }],
		schools: [{ name: 'SCH-1', school_name: 'Main School', abbr: 'MS', organization: 'ORG-1' }],
		teams: [],
		student_groups: [
			{
				name: 'SG-1',
				student_group_name: 'Grade 6 Math',
				student_group_abbreviation: 'G6 Math',
				school: 'SCH-1',
			},
		],
	},
	permissions: {
		can_create: true,
		can_target_wide_school_scope: false,
	},
};

const wideAudienceQuickCreateOptions = {
	...quickCreateOptions,
	fields: {
		...quickCreateOptions.fields,
		audience_target_modes: ['School Scope', 'Organization', 'Team', 'Student Group'],
	},
	recipient_rules: {
		...quickCreateOptions.recipient_rules,
		Organization: {
			allowed_fields: ['to_guardians', 'to_staff'],
			allowed_labels: ['Guardians', 'Staff'],
			default_fields: ['to_staff'],
		},
	},
	permissions: {
		can_create: true,
		can_target_wide_school_scope: true,
	},
};

const noDefaultSchoolQuickCreateOptions = {
	...quickCreateOptions,
	context: {
		...quickCreateOptions.context,
		default_school: null,
		allowed_schools: ['SCH-1', 'SCH-2'],
	},
	references: {
		...quickCreateOptions.references,
		schools: [
			{ name: 'SCH-1', school_name: 'Main School', abbr: 'MS', organization: 'ORG-1' },
			{ name: 'SCH-2', school_name: 'South School', abbr: 'SS', organization: 'ORG-1' },
		],
	},
};

const interactiveThreadQuickCreateOptions = {
	...quickCreateOptions,
	fields: {
		...quickCreateOptions.fields,
		interaction_modes: ['None', 'Student Q&A', 'Structured Feedback', 'Staff Comments'],
		portal_surfaces: ['Desk', 'Morning Brief'],
		priorities: ['Normal', 'High'],
	},
};

const everywhereQuickCreateOptions = {
	...quickCreateOptions,
	defaults: {
		...quickCreateOptions.defaults,
		portal_surface: 'Everywhere',
	},
	fields: {
		...quickCreateOptions.fields,
		portal_surfaces: ['Desk', 'Everywhere'],
	},
};

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountModal(props: Record<string, unknown> = {}) {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(OrgCommunicationQuickCreateModal, {
					open: true,
					entryMode: 'staff-home',
					title: 'Weekly staff update',
					...props,
				});
			},
		})
	);

	app.mount(host);
	cleanupFns.push(() => {
		app.unmount();
		host.remove();
	});
}

function clickRecipient(labelText: string) {
	setCheckboxByLabel(labelText, true);
}

function setCheckboxByLabel(labelText: string, checked: boolean) {
	const label = Array.from(document.querySelectorAll('label')).find(node =>
		(node.textContent || '').includes(labelText)
	);
	const input = label?.querySelector('input[type="checkbox"]') as HTMLInputElement | null;
	if (!input) return;
	input.checked = checked;
	input.dispatchEvent(new Event('change', { bubbles: true }));
}

function clickButton(labelText: string) {
	const button = Array.from(document.querySelectorAll('button')).find(node =>
		(node.textContent || '').includes(labelText)
	);
	button?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
}

function setPublishFrom(value: string) {
	const input = document.querySelector('input[type="datetime-local"]') as HTMLInputElement | null;
	if (!input) return;
	input.value = value;
	input.dispatchEvent(new Event('input', { bubbles: true }));
}

function setRichMessage(value: string) {
	const editor = document.querySelector('[data-text-editor="true"]') as HTMLTextAreaElement | null;
	if (!editor) return;
	editor.value = value;
	editor.dispatchEvent(new Event('input', { bubbles: true }));
}

function clickEditorToolbarButton(label: string) {
	const button = document.querySelector(
		`[data-editor-toolbar-button="${label}"]`
	) as HTMLButtonElement | null;
	button?.click();
}

function setInputByPlaceholder(placeholder: string, value: string) {
	const input = Array.from(document.querySelectorAll('input')).find(node =>
		(node.getAttribute('placeholder') || '').includes(placeholder)
	) as HTMLInputElement | undefined;
	if (!input) return;
	input.value = value;
	input.dispatchEvent(new Event('input', { bubbles: true }));
}

function setSelectByLabel(labelText: string, value: string) {
	const select = getSelectByLabel(labelText);
	if (!select) return;
	select.value = value;
	select.dispatchEvent(new Event('change', { bubbles: true }));
}

function getSelectByLabel(labelText: string) {
	const label = Array.from(document.querySelectorAll('label')).find(node =>
		(node.textContent || '').includes(labelText)
	);
	return label?.parentElement?.querySelector('select') as HTMLSelectElement | null;
}

afterEach(() => {
	addOrgCommunicationLinkMock.mockReset();
	createOrgCommunicationQuickMock.mockReset();
	getOptionsMock.mockReset();
	removeOrgCommunicationAttachmentMock.mockReset();
	uploadOrgCommunicationAttachmentMock.mockReset();
	while (cleanupFns.length) cleanupFns.pop()?.();
	document.body.innerHTML = '';
});

describe('OrgCommunicationQuickCreateModal', () => {
	it('publishes immediately from the staff-home footer action', async () => {
		getOptionsMock.mockResolvedValue(quickCreateOptions);
		createOrgCommunicationQuickMock.mockResolvedValue({
			ok: true,
			status: 'created',
			name: 'COMM-0001',
			title: 'Weekly staff update',
		});

		mountModal();
		await flushUi();

		clickRecipient('Students');
		await flushUi();
		clickButton('Publish');
		await flushUi();

		expect(createOrgCommunicationQuickMock).toHaveBeenCalledTimes(1);
		expect(createOrgCommunicationQuickMock.mock.calls[0][0]).toMatchObject({
			title: 'Weekly staff update',
			status: 'Published',
		});
	});

	it('saves a draft from the dedicated footer action', async () => {
		getOptionsMock.mockResolvedValue(quickCreateOptions);
		createOrgCommunicationQuickMock.mockResolvedValue({
			ok: true,
			status: 'created',
			name: 'COMM-0002',
			title: 'Weekly staff update',
		});

		mountModal();
		await flushUi();

		clickRecipient('Students');
		await flushUi();
		clickButton('Save as draft');
		await flushUi();

		expect(createOrgCommunicationQuickMock).toHaveBeenCalledTimes(1);
		expect(createOrgCommunicationQuickMock.mock.calls[0][0]).toMatchObject({
			title: 'Weekly staff update',
			status: 'Draft',
		});
	});

	it('turns Publish into Scheduled when Publish from is in the future', async () => {
		getOptionsMock.mockResolvedValue(quickCreateOptions);
		createOrgCommunicationQuickMock.mockResolvedValue({
			ok: true,
			status: 'created',
			name: 'COMM-0003',
			title: 'Weekly staff update',
		});

		mountModal();
		await flushUi();

		clickRecipient('Students');
		setPublishFrom('2099-03-21T09:30');
		await flushUi();
		clickButton('Publish');
		await flushUi();

		expect(createOrgCommunicationQuickMock).toHaveBeenCalledTimes(1);
		expect(createOrgCommunicationQuickMock.mock.calls[0][0]).toMatchObject({
			title: 'Weekly staff update',
			status: 'Scheduled',
			publish_from: '2099-03-21 09:30:00',
		});
	});

	it('submits rich-text message HTML from the overlay editor', async () => {
		getOptionsMock.mockResolvedValue(quickCreateOptions);
		createOrgCommunicationQuickMock.mockResolvedValue({
			ok: true,
			status: 'created',
			name: 'COMM-0004',
			title: 'Weekly staff update',
		});

		mountModal();
		await flushUi();

		setRichMessage('<p><strong>Important</strong> update</p><ul><li>Agenda</li></ul>');
		clickRecipient('Students');
		await flushUi();
		clickButton('Publish');
		await flushUi();

		expect(createOrgCommunicationQuickMock).toHaveBeenCalledTimes(1);
		expect(createOrgCommunicationQuickMock.mock.calls[0][0]).toMatchObject({
			message: '<p><strong>Important</strong> update</p><ul><li>Agenda</li></ul>',
		});
	});

	it('renders the ready-check card with a solid canopy fallback background', async () => {
		getOptionsMock.mockResolvedValue(quickCreateOptions);

		mountModal();
		await flushUi();

		const readyCheckCard = document.querySelector('.if-org-communication-ready-check');
		expect(readyCheckCard).toBeTruthy();
		expect(readyCheckCard?.getAttribute('class') || '').toContain('bg-canopy');
	});

	it('keeps publish and brief date controls in dedicated two-column groups', async () => {
		getOptionsMock.mockResolvedValue(interactiveThreadQuickCreateOptions);

		mountModal();
		await flushUi();

		const publishWindowGrid = document.querySelector('.if-org-communication-publish-window-grid');
		const briefWindowGrid = document.querySelector('.if-org-communication-brief-window-grid');

		expect(publishWindowGrid?.textContent || '').toContain('Publish from');
		expect(publishWindowGrid?.textContent || '').toContain('Publish until');
		expect(publishWindowGrid?.getAttribute('class') || '').toContain('min-[480px]:grid-cols-2');

		expect(briefWindowGrid?.textContent || '').toContain('Brief start date');
		expect(briefWindowGrid?.textContent || '').toContain('Brief end date');
		expect(briefWindowGrid?.getAttribute('class') || '').toContain('min-[480px]:grid-cols-2');
	});

	it('keeps delivery select controls in a dedicated two-column group', async () => {
		getOptionsMock.mockResolvedValue(interactiveThreadQuickCreateOptions);

		mountModal();
		await flushUi();

		const deliverySelectGrid = document.querySelector(
			'.if-org-communication-delivery-select-grid'
		);

		expect(deliverySelectGrid?.textContent || '').toContain('Priority');
		expect(deliverySelectGrid?.textContent || '').toContain('Portal surface');
		expect(deliverySelectGrid?.getAttribute('class') || '').toContain(
			'min-[480px]:grid-cols-2'
		);
	});

	it('opens the native picker when a delivery date input is clicked', async () => {
		getOptionsMock.mockResolvedValue(interactiveThreadQuickCreateOptions);

		const showPickerMock = vi.fn();
		Object.defineProperty(HTMLInputElement.prototype, 'showPicker', {
			configurable: true,
			value: showPickerMock,
		});

		mountModal();
		await flushUi();

		const publishInput = document.querySelector(
			'.if-org-communication-publish-window-grid input[type="datetime-local"]'
		) as HTMLInputElement | null;
		publishInput?.dispatchEvent(new MouseEvent('click', { bubbles: true }));

		expect(showPickerMock).toHaveBeenCalledTimes(1);

		Reflect.deleteProperty(HTMLInputElement.prototype, 'showPicker');
	});

	it('keeps the ready-check card at the bottom of the staff-home aside', async () => {
		getOptionsMock.mockResolvedValue(quickCreateOptions);

		mountModal();
		await flushUi();

		const readyCheckCard = document.querySelector('.if-org-communication-ready-check');
		const previousSection = readyCheckCard?.previousElementSibling as HTMLElement | null;
		const nextSection = readyCheckCard?.nextElementSibling as HTMLElement | null;

		expect(previousSection?.textContent || '').toContain('Audience summary');
		expect(nextSection).toBeNull();
	});

	it('submits organization staff rows as staff-only audiences', async () => {
		getOptionsMock.mockResolvedValue(wideAudienceQuickCreateOptions);
		createOrgCommunicationQuickMock.mockResolvedValue({
			ok: true,
			status: 'created',
			name: 'COMM-0005',
			title: 'Weekly staff update',
		});

		mountModal();
		await flushUi();

		clickButton('Organization');
		await flushUi();
		clickButton('Publish');
		await flushUi();

		expect(createOrgCommunicationQuickMock).toHaveBeenCalledTimes(1);
		expect(createOrgCommunicationQuickMock.mock.calls[0][0].audiences).toEqual([
			expect.objectContaining({
				target_mode: 'Organization',
				school: null,
				team: null,
					student_group: null,
					include_descendants: 0,
					to_staff: 1,
					to_students: 0,
					to_guardians: 0,
				}),
			]);
	});

	it('clears the issuing school when an organization audience is selected', async () => {
		getOptionsMock.mockResolvedValue(wideAudienceQuickCreateOptions);

		mountModal();
		await flushUi();

		const issuingSchool = getSelectByLabel('Issuing school');
		expect(issuingSchool?.value).toBe('SCH-1');

		clickButton('Organization');
		await flushUi();

		expect(issuingSchool?.value).toBe('');
		expect(issuingSchool?.disabled).toBe(true);
	});

	it('submits organization guardian rows without forcing staff recipients', async () => {
		getOptionsMock.mockResolvedValue(wideAudienceQuickCreateOptions);
		createOrgCommunicationQuickMock.mockResolvedValue({
			ok: true,
			status: 'created',
			name: 'COMM-0005-GUARDIANS',
			title: 'Weekly staff update',
		});

		mountModal();
		await flushUi();

		clickButton('Organization');
		await flushUi();
		setCheckboxByLabel('Guardians', true);
		setCheckboxByLabel('Staff', false);
		await flushUi();
		clickButton('Publish');
		await flushUi();

		expect(createOrgCommunicationQuickMock).toHaveBeenCalledTimes(1);
		expect(createOrgCommunicationQuickMock.mock.calls[0][0].audiences).toEqual([
			expect.objectContaining({
				target_mode: 'Organization',
				school: null,
				team: null,
				student_group: null,
				include_descendants: 0,
				to_staff: 0,
				to_students: 0,
				to_guardians: 1,
			}),
		]);
	});

	it('renders a compact locked composer for class-event mode', async () => {
		getOptionsMock.mockResolvedValue(quickCreateOptions);

		mountModal({
			entryMode: 'class-event',
			title: '25-26-G6-Math1/IIS 2025-2026',
			studentGroup: 'SG-1',
			school: 'SCH-1',
			sessionDate: '2026-04-03',
			sessionTimeLabel: '8:00 AM - 8:45 AM',
			courseLabel: 'IB MYP mathematics (Grade 6)',
		});
		await flushUi();

		const text = document.body.textContent || '';
		expect(text).toContain('Locked context');
		expect(text).toContain('Send options');
		expect(text).not.toContain('Communication type');
		expect(text).not.toContain('Organization');
		expect(text).not.toContain('Thread settings');
		expect(document.querySelector('.if-org-communication-ready-check')).toBeNull();
		expect(document.querySelectorAll('.if-class-event-context-card')).toHaveLength(1);
		expect(document.querySelectorAll('.if-class-event-context-pill')).toHaveLength(4);
		expect(
			document.querySelector('.if-class-event-audience-grid')?.getAttribute('class') || ''
		).toContain('min-[480px]:grid-cols-2');
		expect(text).toContain('Auto applied');
	});

	it('does not submit the form when a rich-text toolbar control is clicked', async () => {
		getOptionsMock.mockResolvedValue(quickCreateOptions);

		mountModal({
			entryMode: 'class-event',
			title: '25-26-G6-Math1/IIS 2025-2026',
			studentGroup: 'SG-1',
			school: 'SCH-1',
			sessionDate: '2026-04-03',
			sessionTimeLabel: '8:00 AM - 8:45 AM',
			courseLabel: 'IB MYP mathematics (Grade 6)',
		});
		await flushUi();

		setRichMessage('<p>Keep this draft open</p>');
		clickEditorToolbarButton('Bold');
		await flushUi();

		expect(createOrgCommunicationQuickMock).not.toHaveBeenCalled();
		const editor = document.querySelector('[data-text-editor="true"]') as HTMLTextAreaElement | null;
		expect(editor?.value).toBe('<p>Keep this draft open</p>');
	});

	it('keeps interaction settings aligned to the selected interaction mode', async () => {
		getOptionsMock.mockResolvedValue(interactiveThreadQuickCreateOptions);

		mountModal();
		await flushUi();

		const privateNotesLabel = Array.from(document.querySelectorAll('label')).find(node =>
			(node.textContent || '').includes('Let teachers and staff reply privately.')
		);
		const publicThreadLabel = Array.from(document.querySelectorAll('label')).find(node =>
			(node.textContent || '').includes('Let students or families reply in the shared thread.')
		);

		const privateNotesInput = privateNotesLabel?.querySelector('input') as HTMLInputElement | null;
		const publicThreadInput = publicThreadLabel?.querySelector('input') as HTMLInputElement | null;

		setSelectByLabel('Interaction mode', 'Student Q&A');
		await flushUi();

		expect(privateNotesInput?.disabled).toBe(true);
		expect(publicThreadInput?.disabled).toBe(false);

		publicThreadInput?.click();
		await flushUi();

		expect(privateNotesInput?.checked).toBe(false);
		expect(publicThreadInput?.checked).toBe(true);

		setSelectByLabel('Interaction mode', 'Structured Feedback');
		await flushUi();

		expect(privateNotesInput?.disabled).toBe(false);
		expect(publicThreadInput?.disabled).toBe(false);

		privateNotesInput?.click();
		await flushUi();

		expect(privateNotesInput?.checked).toBe(true);
		expect(publicThreadInput?.checked).toBe(true);
	});

	it('submits class-event payload with guardian visibility off by default', async () => {
		getOptionsMock.mockResolvedValue(quickCreateOptions);
		createOrgCommunicationQuickMock.mockResolvedValue({
			ok: true,
			status: 'created',
			name: 'COMM-0006',
			title: '25-26-G6-Math1/IIS 2025-2026',
		});

		mountModal({
			entryMode: 'class-event',
			title: '25-26-G6-Math1/IIS 2025-2026',
			studentGroup: 'SG-1',
			school: 'SCH-1',
			sessionDate: '2026-04-03',
			sessionTimeLabel: '8:00 AM - 8:45 AM',
			courseLabel: 'IB MYP mathematics (Grade 6)',
		});
		await flushUi();

		clickButton('Publish announcement');
		await flushUi();

		expect(createOrgCommunicationQuickMock).toHaveBeenCalledTimes(1);
		expect(createOrgCommunicationQuickMock.mock.calls[0][0]).toMatchObject({
			title: '25-26-G6-Math1/IIS 2025-2026',
			communication_type: 'Class Announcement',
			status: 'Published',
			portal_surface: 'Everywhere',
			organization: 'ORG-1',
			school: 'SCH-1',
			interaction_mode: 'None',
			allow_private_notes: 0,
			allow_public_thread: 0,
			audiences: [
				expect.objectContaining({
					target_mode: 'Student Group',
						student_group: 'SG-1',
						to_students: 1,
						to_guardians: 0,
						to_staff: 0,
					}),
				],
			});
	});

	it('lets staff-home save a draft before brief dates are filled for everywhere surface', async () => {
		getOptionsMock.mockResolvedValue(everywhereQuickCreateOptions);
		createOrgCommunicationQuickMock.mockResolvedValue({
			ok: true,
			status: 'created',
			name: 'COMM-DRAFT-EVERYWHERE',
			title: 'Weekly staff update',
		});

		mountModal();
		await flushUi();

		clickRecipient('Guardians');
		await flushUi();
		clickButton('Save as draft');
		await flushUi();

		expect(createOrgCommunicationQuickMock).toHaveBeenCalledTimes(1);
		expect(createOrgCommunicationQuickMock.mock.calls[0][0]).toMatchObject({
			status: 'Draft',
			portal_surface: 'Everywhere',
			brief_start_date: null,
		});
	});

	it('auto-saves a staff-home link draft before brief dates are filled for everywhere surface', async () => {
		getOptionsMock.mockResolvedValue(everywhereQuickCreateOptions);
		createOrgCommunicationQuickMock.mockResolvedValue({
			ok: true,
			status: 'created',
			name: 'COMM-DRAFT-EVERYWHERE-LINK',
			title: 'Weekly staff update',
		});
		addOrgCommunicationLinkMock.mockResolvedValue({
			ok: true,
			org_communication: 'COMM-DRAFT-EVERYWHERE-LINK',
			attachment: {
				row_name: 'row-link-everywhere',
				kind: 'link',
				title: 'Health advisory',
				external_url: 'https://example.com/health-advisory',
				open_url: 'https://example.com/health-advisory',
			},
		});

		mountModal();
		await flushUi();

		clickRecipient('Guardians');
		await flushUi();
		clickButton('Add link');
		await flushUi();
		setInputByPlaceholder('https://example.com/resource.pdf', 'https://example.com/health-advisory');
		setInputByPlaceholder('Optional display label', 'Health advisory');
		await flushUi();
		clickButton('Add link');
		await flushUi();

		expect(createOrgCommunicationQuickMock).toHaveBeenCalledTimes(1);
		expect(createOrgCommunicationQuickMock.mock.calls[0][0]).toMatchObject({
			status: 'Draft',
			portal_surface: 'Everywhere',
			brief_start_date: null,
		});
		expect(addOrgCommunicationLinkMock).toHaveBeenCalledWith({
			org_communication: 'COMM-DRAFT-EVERYWHERE-LINK',
			title: 'Health advisory',
			external_url: 'https://example.com/health-advisory',
		});
		expect(document.body.textContent || '').toContain('Health advisory');
	});

	it('auto-saves a class-event draft before adding a link attachment and publishes by update', async () => {
		getOptionsMock.mockResolvedValue(quickCreateOptions);
		createOrgCommunicationQuickMock
			.mockResolvedValueOnce({
				ok: true,
				status: 'created',
				name: 'COMM-DRAFT-1',
				title: '25-26-G6-Math1/IIS 2025-2026',
			})
			.mockResolvedValueOnce({
				ok: true,
				status: 'updated',
				name: 'COMM-DRAFT-1',
				title: '25-26-G6-Math1/IIS 2025-2026',
			});
		addOrgCommunicationLinkMock.mockResolvedValue({
			ok: true,
			org_communication: 'COMM-DRAFT-1',
			attachment: {
				row_name: 'row-link',
				kind: 'link',
				title: 'Reference sheet',
				external_url: 'https://example.com/reference',
				open_url: 'https://example.com/reference',
			},
		});

		mountModal({
			entryMode: 'class-event',
			title: '25-26-G6-Math1/IIS 2025-2026',
			studentGroup: 'SG-1',
			school: 'SCH-1',
			sessionDate: '2026-04-03',
			sessionTimeLabel: '8:00 AM - 8:45 AM',
			courseLabel: 'IB MYP mathematics (Grade 6)',
		});
		await flushUi();

		clickButton('Add link');
		await flushUi();
		setInputByPlaceholder('https://example.com/resource.pdf', 'https://example.com/reference');
		setInputByPlaceholder('Optional display label', 'Reference sheet');
		await flushUi();
		clickButton('Add link');
		await flushUi();
		clickButton('Publish announcement');
		await flushUi();

		expect(createOrgCommunicationQuickMock).toHaveBeenNthCalledWith(
			1,
			expect.objectContaining({
				name: null,
				status: 'Draft',
			})
		);
		expect(addOrgCommunicationLinkMock).toHaveBeenCalledWith({
			org_communication: 'COMM-DRAFT-1',
			title: 'Reference sheet',
			external_url: 'https://example.com/reference',
		});
		expect(createOrgCommunicationQuickMock).toHaveBeenNthCalledWith(
			2,
			expect.objectContaining({
				name: 'COMM-DRAFT-1',
				status: 'Published',
			})
		);
		expect(document.body.textContent || '').toContain('Reference sheet');
	});

	it('auto-saves a staff-home draft before adding a link attachment and publishes by update', async () => {
		getOptionsMock.mockResolvedValue(quickCreateOptions);
		createOrgCommunicationQuickMock
			.mockResolvedValueOnce({
				ok: true,
				status: 'created',
				name: 'COMM-DRAFT-2',
				title: 'Weekly staff update',
			})
			.mockResolvedValueOnce({
				ok: true,
				status: 'updated',
				name: 'COMM-DRAFT-2',
				title: 'Weekly staff update',
			});
		addOrgCommunicationLinkMock.mockResolvedValue({
			ok: true,
			org_communication: 'COMM-DRAFT-2',
			attachment: {
				row_name: 'row-link-staff',
				kind: 'link',
				title: 'Policy PDF',
				external_url: 'https://example.com/policy.pdf',
				open_url: 'https://example.com/policy.pdf',
			},
		});

		mountModal();
		await flushUi();

		clickRecipient('Students');
		await flushUi();
		clickButton('Add link');
		await flushUi();
		setInputByPlaceholder('https://example.com/resource.pdf', 'https://example.com/policy.pdf');
		setInputByPlaceholder('Optional display label', 'Policy PDF');
		await flushUi();
		clickButton('Add link');
		await flushUi();
		clickButton('Publish');
		await flushUi();

		expect(createOrgCommunicationQuickMock).toHaveBeenNthCalledWith(
			1,
			expect.objectContaining({
				name: null,
				status: 'Draft',
			})
		);
		expect(addOrgCommunicationLinkMock).toHaveBeenCalledWith({
			org_communication: 'COMM-DRAFT-2',
			title: 'Policy PDF',
			external_url: 'https://example.com/policy.pdf',
		});
		expect(createOrgCommunicationQuickMock).toHaveBeenNthCalledWith(
			2,
			expect.objectContaining({
				name: 'COMM-DRAFT-2',
				status: 'Published',
			})
		);
		expect(document.body.textContent || '').toContain('Policy PDF');
	});

	it('auto-saves a draft link before audience school or recipients are filled', async () => {
		getOptionsMock.mockResolvedValue(noDefaultSchoolQuickCreateOptions);
		createOrgCommunicationQuickMock.mockResolvedValue({
			ok: true,
			status: 'created',
			name: 'COMM-DRAFT-INCOMPLETE-AUDIENCE',
			title: 'Weekly staff update',
		});
		addOrgCommunicationLinkMock.mockResolvedValue({
			ok: true,
			org_communication: 'COMM-DRAFT-INCOMPLETE-AUDIENCE',
			attachment: {
				row_name: 'row-link-incomplete-audience',
				kind: 'link',
				title: 'Policy PDF',
				external_url: 'https://example.com/policy.pdf',
				open_url: 'https://example.com/policy.pdf',
			},
		});

		mountModal();
		await flushUi();

		clickButton('Add link');
		await flushUi();
		setInputByPlaceholder('https://example.com/resource.pdf', 'https://example.com/policy.pdf');
		setInputByPlaceholder('Optional display label', 'Policy PDF');
		await flushUi();
		clickButton('Add link');
		await flushUi();

		expect(createOrgCommunicationQuickMock).toHaveBeenCalledTimes(1);
		expect(createOrgCommunicationQuickMock).toHaveBeenCalledWith(
			expect.objectContaining({
				status: 'Draft',
			})
		);
		expect(addOrgCommunicationLinkMock).toHaveBeenCalledWith({
			org_communication: 'COMM-DRAFT-INCOMPLETE-AUDIENCE',
			title: 'Policy PDF',
			external_url: 'https://example.com/policy.pdf',
		});
	});

	it('routes draft-save blockers for attachment actions to the top action banner', async () => {
		getOptionsMock.mockResolvedValue(quickCreateOptions);

		mountModal({ title: '' });
		await flushUi();

		clickButton('Add link');
		await flushUi();
		setInputByPlaceholder('https://example.com/resource.pdf', 'https://example.com/policy.pdf');
		setInputByPlaceholder('Optional display label', 'Policy PDF');
		await flushUi();
		clickButton('Add link');
		await flushUi();

		expect(createOrgCommunicationQuickMock).not.toHaveBeenCalled();
		expect(addOrgCommunicationLinkMock).not.toHaveBeenCalled();
		expect(document.querySelector('[role="alert"]')?.textContent || '').toContain('Title is required.');
		expect(document.querySelector('p.type-caption.text-rose-900')).toBeNull();
	});

	it('keeps true attachment failures inside the attachment section', async () => {
		getOptionsMock.mockResolvedValue(quickCreateOptions);
		createOrgCommunicationQuickMock.mockResolvedValue({
			ok: true,
			status: 'created',
			name: 'COMM-DRAFT-ATTACH-ERROR',
			title: 'Weekly staff update',
		});
		addOrgCommunicationLinkMock.mockRejectedValue(new Error('Attachment policy rejected the link.'));

		mountModal();
		await flushUi();

		clickRecipient('Students');
		await flushUi();
		clickButton('Add link');
		await flushUi();
		setInputByPlaceholder('https://example.com/resource.pdf', 'https://example.com/policy.pdf');
		setInputByPlaceholder('Optional display label', 'Policy PDF');
		await flushUi();
		clickButton('Add link');
		await flushUi();

		expect(createOrgCommunicationQuickMock).toHaveBeenCalledTimes(1);
		expect(addOrgCommunicationLinkMock).toHaveBeenCalledTimes(1);
		expect(document.querySelector('[role="alert"]')).toBeNull();
		expect(document.querySelector('p.type-caption.text-rose-900')?.textContent || '').toContain(
			'Attachment policy rejected the link.'
		);
	});
});
