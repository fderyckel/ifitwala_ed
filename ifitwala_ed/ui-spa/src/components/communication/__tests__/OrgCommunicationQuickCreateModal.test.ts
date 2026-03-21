import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const { createOrgCommunicationQuickMock, getOptionsMock } = vi.hoisted(() => ({
	createOrgCommunicationQuickMock: vi.fn(),
	getOptionsMock: vi.fn(),
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
}));

vi.mock('@/lib/services/orgCommunicationQuickCreateService', () => ({
	createOrgCommunicationQuick: createOrgCommunicationQuickMock,
	getOrgCommunicationQuickCreateOptions: getOptionsMock,
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
		student_groups: [],
	},
	permissions: {
		can_create: true,
		can_target_wide_school_scope: false,
	},
};

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountModal() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(OrgCommunicationQuickCreateModal, {
					open: true,
					entryMode: 'staff-home',
					title: 'Weekly staff update',
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
	const label = Array.from(document.querySelectorAll('label')).find(node =>
		(node.textContent || '').includes(labelText)
	);
	const input = label?.querySelector('input[type="checkbox"]') as HTMLInputElement | null;
	if (!input) return;
	input.checked = true;
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

afterEach(() => {
	createOrgCommunicationQuickMock.mockReset();
	getOptionsMock.mockReset();
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
});
