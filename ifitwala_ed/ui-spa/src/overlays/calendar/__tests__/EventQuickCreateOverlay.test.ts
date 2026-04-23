import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const {
	createMeetingQuickMock,
	createSchoolEventQuickMock,
	getEventQuickCreateOptionsMock,
	getMeetingTeamAttendeesMock,
	searchMeetingAttendeesMock,
	suggestMeetingRoomsMock,
	suggestMeetingSlotsMock,
} = vi.hoisted(() => ({
	createMeetingQuickMock: vi.fn(),
	createSchoolEventQuickMock: vi.fn(),
	getEventQuickCreateOptionsMock: vi.fn(),
	getMeetingTeamAttendeesMock: vi.fn(),
	searchMeetingAttendeesMock: vi.fn(),
	suggestMeetingRoomsMock: vi.fn(),
	suggestMeetingSlotsMock: vi.fn(),
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

vi.mock('@/lib/datetime', () => ({
	formatHumanDateTimeFields: vi.fn(() => 'Formatted slot'),
}));

vi.mock('@/lib/services/calendar/eventQuickCreateService', () => ({
	createMeetingQuick: createMeetingQuickMock,
	createSchoolEventQuick: createSchoolEventQuickMock,
	getEventQuickCreateOptions: getEventQuickCreateOptionsMock,
	getMeetingTeamAttendees: getMeetingTeamAttendeesMock,
	searchMeetingAttendees: searchMeetingAttendeesMock,
	suggestMeetingRooms: suggestMeetingRoomsMock,
	suggestMeetingSlots: suggestMeetingSlotsMock,
}));

import EventQuickCreateOverlay from '@/overlays/calendar/EventQuickCreateOverlay.vue';

const cleanupFns: Array<() => void> = [];

const baseOptions = {
	can_create_meeting: false,
	can_create_school_event: true,
	meeting_categories: [],
	school_event_categories: ['Parent Engagement'],
	audience_types: ['All Guardians', 'Students in Student Group', 'Custom Users'],
	announcement_publish: {
		enabled: true,
		blocked_reason: null,
	},
	schools: [{ value: 'ISS', label: 'Ifitwala Secondary School' }],
	teams: [{ value: 'TEAM-1', label: 'Pastoral Team' }],
	student_groups: [{ value: 'SG-1', label: 'MYP 1' }],
	locations: [],
	locations_by_school: { ISS: [] },
	location_types: [],
	location_types_by_school: { ISS: [] },
	attendee_kinds: [],
	defaults: {
		school: 'ISS',
		day_start_time: '08:00',
		day_end_time: '17:00',
		duration_minutes: 60,
	},
};

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountOverlay(props: Record<string, unknown> = {}) {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(EventQuickCreateOverlay, {
					open: true,
					eventType: 'school_event',
					lockEventType: true,
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

function getLabelElement(labelText: string) {
	return Array.from(document.querySelectorAll('label')).find(label =>
		(label.textContent || '').includes(labelText)
	) as HTMLLabelElement | undefined;
}

function getSelectByLabel(labelText: string) {
	return getLabelElement(labelText)?.parentElement?.querySelector(
		'select'
	) as HTMLSelectElement | null;
}

function getTextareaByLabel(labelText: string) {
	return getLabelElement(labelText)?.parentElement?.querySelector(
		'textarea'
	) as HTMLTextAreaElement | null;
}

function setInputByPlaceholder(placeholder: string, value: string) {
	const input = document.querySelector(
		`input[placeholder="${placeholder}"]`
	) as HTMLInputElement | null;
	if (!input) throw new Error(`Missing input with placeholder: ${placeholder}`);
	input.value = value;
	input.dispatchEvent(new Event('input', { bubbles: true }));
}

function clickButton(text: string) {
	const button = Array.from(document.querySelectorAll('button')).find(
		element => (element.textContent || '').trim() === text
	) as HTMLButtonElement | undefined;
	if (!button) throw new Error(`Missing button: ${text}`);
	button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
}

afterEach(() => {
	createMeetingQuickMock.mockReset();
	createSchoolEventQuickMock.mockReset();
	getEventQuickCreateOptionsMock.mockReset();
	getMeetingTeamAttendeesMock.mockReset();
	searchMeetingAttendeesMock.mockReset();
	suggestMeetingRoomsMock.mockReset();
	suggestMeetingSlotsMock.mockReset();
	while (cleanupFns.length) cleanupFns.pop()?.();
	document.body.innerHTML = '';
});

describe('EventQuickCreateOverlay school event publishing', () => {
	it('explains the calendar vs announcement split and disables publish when capability is blocked', async () => {
		getEventQuickCreateOptionsMock.mockResolvedValue({
			...baseOptions,
			announcement_publish: {
				enabled: false,
				blocked_reason: 'Set a default organization before publishing announcements.',
			},
		});

		mountOverlay();
		await flushUi();

		const publishLabel = getLabelElement('Also publish announcement');
		const publishCheckbox = publishLabel?.querySelector('input[type="checkbox"]') as
			| HTMLInputElement
			| undefined;

		expect(document.body.textContent || '').toContain('Calendar item vs announcement');
		expect(document.body.textContent || '').toContain(
			'Set a default organization before publishing announcements.'
		);
		expect(publishCheckbox?.disabled).toBe(true);
	});

	it('submits a combined create-and-publish payload from the school event workflow', async () => {
		getEventQuickCreateOptionsMock.mockResolvedValue(baseOptions);
		createSchoolEventQuickMock.mockResolvedValue({
			ok: true,
			status: 'created',
			idempotent: false,
			doctype: 'School Event',
			name: 'SE-26-04-00001',
			title: 'Parent MYP Workshop',
			start: '2026-04-22T08:00:00+07:00',
			end: '2026-04-22T09:00:00+07:00',
			target_doctype: 'School Event',
			target_name: 'SE-26-04-00001',
			target_url: '/desk/school-event/SE-26-04-00001',
			target_label: 'Parent MYP Workshop',
			published_communication: {
				name: 'ORG-COMM-26-04-00001',
				title: 'Parent MYP Workshop',
				status: 'created',
			},
		});

		mountOverlay();
		await flushUi();

		setInputByPlaceholder('Parent workshop: assessment reporting', 'Parent MYP Workshop');

		const publishCheckbox = getLabelElement('Also publish announcement')?.querySelector(
			'input[type="checkbox"]'
		) as HTMLInputElement | null;
		if (!publishCheckbox) throw new Error('Missing publish checkbox');
		publishCheckbox.checked = true;
		publishCheckbox?.dispatchEvent(new Event('change', { bubbles: true }));
		await flushUi();

		const messageTextarea = getTextareaByLabel('Announcement message (optional)');
		if (!messageTextarea) throw new Error('Missing announcement message textarea');
		messageTextarea.value = 'Workshop presentation';
		messageTextarea.dispatchEvent(new Event('input', { bubbles: true }));
		await flushUi();

		clickButton('Create event and publish');
		await flushUi();

		expect(createSchoolEventQuickMock).toHaveBeenCalledTimes(1);
		expect(createSchoolEventQuickMock.mock.calls[0][0]).toMatchObject({
			subject: 'Parent MYP Workshop',
			school: 'ISS',
			audience_type: 'All Guardians',
			publish_announcement: 1,
			announcement_message: 'Workshop presentation',
		});
	});
});
