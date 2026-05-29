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

function getInputByLabel(labelText: string) {
	return getLabelElement(labelText)?.parentElement?.querySelector(
		'input'
	) as HTMLInputElement | null;
}

function getCheckboxByLabel(labelText: string) {
	return getLabelElement(labelText)?.querySelector('input[type="checkbox"]') as
		| HTMLInputElement
		| null;
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

function updateSelectByLabel(labelText: string, value: string) {
	const select = getSelectByLabel(labelText);
	if (!select) throw new Error(`Missing select with label: ${labelText}`);
	select.value = value;
	select.dispatchEvent(new Event('change', { bubbles: true }));
}

async function waitForDebouncedSearch() {
	await new Promise(resolve => window.setTimeout(resolve, 320));
	await flushUi();
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

describe('EventQuickCreateOverlay meeting attendees', () => {
	it('defaults attendee search to employees and expands only after explicit student or guardian opt-in', async () => {
		getEventQuickCreateOptionsMock.mockResolvedValue({
			...baseOptions,
			can_create_meeting: true,
			can_create_school_event: false,
			attendee_kinds: [
				{ value: 'employee', label: 'Employees' },
				{ value: 'student', label: 'Students' },
				{ value: 'guardian', label: 'Guardians' },
			],
		});
		searchMeetingAttendeesMock.mockResolvedValue({ results: [], notes: [] });

		mountOverlay({
			eventType: 'meeting',
			lockEventType: true,
			meetingMode: 'ad_hoc',
		});
		await flushUi();

		setInputByPlaceholder('Search by name or email', 'car');
		await waitForDebouncedSearch();

		expect(searchMeetingAttendeesMock).toHaveBeenLastCalledWith({
			query: 'car',
			attendee_kinds: ['employee'],
			limit: 12,
		});

		const studentsCheckbox = getCheckboxByLabel('Students');
		const guardiansCheckbox = getCheckboxByLabel('Guardians');
		if (!studentsCheckbox || !guardiansCheckbox) throw new Error('Missing invite-scope checkboxes');
		studentsCheckbox.checked = true;
		studentsCheckbox.dispatchEvent(new Event('change', { bubbles: true }));
		guardiansCheckbox.checked = true;
		guardiansCheckbox.dispatchEvent(new Event('change', { bubbles: true }));
		await waitForDebouncedSearch();

		expect(searchMeetingAttendeesMock).toHaveBeenLastCalledWith({
			query: 'car',
			attendee_kinds: ['employee', 'student', 'guardian'],
			limit: 12,
		});
		expect(document.body.textContent || '').toContain(
			'Students and guardians will appear in search and can receive this meeting invite.'
		);
	});

	it('blocks submit when a selected student no longer matches the invite scope', async () => {
		getEventQuickCreateOptionsMock.mockResolvedValue({
			...baseOptions,
			can_create_meeting: true,
			can_create_school_event: false,
			attendee_kinds: [
				{ value: 'employee', label: 'Employees' },
				{ value: 'student', label: 'Students' },
			],
		});
		getMeetingTeamAttendeesMock.mockResolvedValue({
			team: 'TEAM-1',
			results: [
				{
					value: 'student@example.com',
					label: 'Student Example',
					meta: 'ISS',
					kind: 'student',
					availability_mode: 'school_schedule',
				},
			],
			notes: [],
		});

		mountOverlay({
			eventType: 'meeting',
			lockEventType: true,
			meetingMode: 'ad_hoc',
		});
		await flushUi();

		setInputByPlaceholder('Family support meeting', 'Private Meeting');
		const studentsCheckbox = getCheckboxByLabel('Students');
		if (!studentsCheckbox) throw new Error('Missing Students checkbox');
		studentsCheckbox.checked = true;
		studentsCheckbox.dispatchEvent(new Event('change', { bubbles: true }));
		updateSelectByLabel('Bulk-add a team', 'TEAM-1');
		await flushUi();
		studentsCheckbox.checked = false;
		studentsCheckbox.dispatchEvent(new Event('change', { bubbles: true }));
		await flushUi();

		clickButton('Create meeting');
		await flushUi();

		expect(createMeetingQuickMock).not.toHaveBeenCalled();
		expect(document.body.textContent || '').toContain(
			'Remove selected student invitees or re-enable Students before creating the meeting.'
		);
	});

	it('bulk-adds team attendees when an ad-hoc meeting team is selected', async () => {
		getEventQuickCreateOptionsMock.mockResolvedValue({
			...baseOptions,
			can_create_meeting: true,
			can_create_school_event: false,
			attendee_kinds: [{ value: 'employee', label: 'Employees' }],
		});
		getMeetingTeamAttendeesMock.mockResolvedValue({
			team: 'TEAM-1',
			results: [
				{
					value: 'teacher@example.com',
					label: 'Teacher Example',
					meta: 'TEAM-1',
					kind: 'employee',
					availability_mode: 'authoritative',
				},
			],
		});

		mountOverlay({
			eventType: 'meeting',
			lockEventType: true,
			meetingMode: 'ad_hoc',
		});
		await flushUi();

		updateSelectByLabel('Bulk-add a team', 'TEAM-1');
		await flushUi();

		expect(getMeetingTeamAttendeesMock).toHaveBeenCalledWith({ team: 'TEAM-1' });
		expect(document.body.textContent || '').toContain('Teacher Example');
		expect(document.body.textContent || '').toContain('1 invitee + organizer');
	});

	it('keeps common-time suggestions visible when the server normalizes duration on first click', async () => {
		getEventQuickCreateOptionsMock.mockResolvedValue({
			...baseOptions,
			can_create_meeting: true,
			can_create_school_event: false,
			attendee_kinds: [{ value: 'employee', label: 'Employees' }],
		});
		getMeetingTeamAttendeesMock.mockResolvedValue({
			team: 'TEAM-1',
			results: [
				{
					value: 'teacher@example.com',
					label: 'Teacher Example',
					meta: 'TEAM-1',
					kind: 'employee',
					availability_mode: 'authoritative',
				},
			],
		});
		suggestMeetingSlotsMock.mockResolvedValue({
			slots: [
				{
					start: '2026-05-29T10:00:00+07:00',
					end: '2026-05-29T11:00:00+07:00',
					date: '2026-05-29',
					start_time: '10:00',
					end_time: '11:00',
					label: 'Friday 10:00',
					blocked_count: 0,
					available_room_count: 1,
					suggested_room: {
						value: 'D204',
						label: 'D204',
						location_type: null,
						location_type_name: null,
						max_capacity: 20,
					},
				},
			],
			fallback_slots: [],
			notes: ['Exact matches already include at least one free room.'],
			duration_minutes: 60,
			attendees: [],
		});

		mountOverlay({
			eventType: 'meeting',
			lockEventType: true,
			meetingMode: 'ad_hoc',
		});
		await flushUi();

		updateSelectByLabel('Bulk-add a team', 'TEAM-1');
		await flushUi();
		const durationInput = getInputByLabel('Duration (minutes)');
		if (!durationInput) throw new Error('Missing duration input');
		durationInput.value = '060';
		durationInput.dispatchEvent(new Event('input', { bubbles: true }));
		await flushUi();

		clickButton('Find common times');
		await flushUi();

		expect(suggestMeetingSlotsMock).toHaveBeenCalledTimes(1);
		expect(suggestMeetingSlotsMock).toHaveBeenCalledWith(
			expect.objectContaining({
				duration_minutes: 60,
				attendees: [
					{
						user: 'teacher@example.com',
						kind: 'employee',
						label: 'Teacher Example',
					},
				],
			})
		);
		expect(document.body.textContent || '').toContain('Friday 10:00');
		expect(document.body.textContent || '').toContain(
			'Exact matches already include at least one free room.'
		);
	});

	it('offers room suggestions when create is blocked by a booked room', async () => {
		getEventQuickCreateOptionsMock.mockResolvedValue({
			...baseOptions,
			can_create_meeting: true,
			can_create_school_event: false,
			attendee_kinds: [{ value: 'employee', label: 'Employees' }],
			locations: [
				{ value: 'D202', label: 'D202', location_type: null, max_capacity: 20, is_group: 0 },
			],
			locations_by_school: {
				ISS: [
					{ value: 'D202', label: 'D202', location_type: null, max_capacity: 20, is_group: 0 },
				],
			},
		});
		getMeetingTeamAttendeesMock.mockResolvedValue({
			team: 'TEAM-1',
			results: [
				{
					value: 'teacher@example.com',
					label: 'Teacher Example',
					meta: 'TEAM-1',
					kind: 'employee',
					availability_mode: 'authoritative',
				},
			],
		});
		createMeetingQuickMock.mockRejectedValue({
			_server_messages: JSON.stringify([
				JSON.stringify({
					message:
						'Location D202 is already booked:<br>Student Group 25-26-G6-Eng/IIS 2025-2026 from 29-05-2026 10:15:00 to 29-05-2026 11:10:00',
					title: 'Location Conflict',
				}),
			]),
			exc_type: 'ValidationError',
		});
		suggestMeetingRoomsMock.mockResolvedValue({
			rooms: [
				{
					value: 'D204',
					label: 'D204',
					building: null,
					location_type: null,
					location_type_name: null,
					max_capacity: 20,
				},
			],
			notes: [],
		});

		mountOverlay({
			eventType: 'meeting',
			lockEventType: true,
			meetingMode: 'ad_hoc',
		});
		await flushUi();

		setInputByPlaceholder('Family support meeting', 'Workflow');
		updateSelectByLabel('Bulk-add a team', 'TEAM-1');
		await flushUi();
		updateSelectByLabel('Location (optional)', 'D202');
		await flushUi();

		clickButton('Create meeting');
		await flushUi();

		expect(document.body.textContent || '').toContain('Location D202 is already booked:');
		expect(document.body.textContent || '').toContain(
			'Use room suggestions to replace the booked room'
		);
		expect(document.body.textContent || '').not.toContain('<br>');

		clickButton('Suggest rooms');
		await flushUi();

		expect(suggestMeetingRoomsMock).toHaveBeenCalledWith(
			expect.objectContaining({
				school: 'ISS',
				location_type: null,
				capacity_needed: 2,
				limit: 8,
			})
		);
		expect(document.body.textContent || '').toContain('D204');
	});
});
