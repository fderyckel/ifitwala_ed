import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const {
	overlayOpenMock,
	analyticsSubmitMock,
	headerSubmitMock,
	freeRoomsSubmitMock,
	locationCalendarState,
	roomUtilizationState,
} =
	vi.hoisted(() => ({
		overlayOpenMock: vi.fn(),
		analyticsSubmitMock: vi.fn(),
		headerSubmitMock: vi.fn(),
		freeRoomsSubmitMock: vi.fn(),
		roomUtilizationState: {
			analyticsAllowed: 0,
		},
		locationCalendarState: {
			data: {
				locations: [{ value: 'SCI-LAB', label: 'Science Lab' }],
				events: [],
				selected_location_label: null,
				note: 'Select a location or building to load its calendar.',
			},
		},
	}));

vi.mock('frappe-ui', async () => {
	const { defineComponent, h, reactive } = await import('vue');

	function createMockResource(initialData: any = null) {
		const state = reactive({
			data: initialData,
			loading: false,
			async submit(_payload?: any) {
				return state.data;
			},
		});
		return state;
	}

	return {
		createResource: ({ url, auto }: { url: string; auto?: boolean }) => {
			if (url.includes('get_room_utilization_filter_meta')) {
				return createMockResource({
					schools: [{ name: 'ISS', label: 'Ifitwala Secondary School' }],
					default_school: 'ISS',
					location_types: [],
					time_util_defaults_by_school: {
						ISS: {
							day_start_time: '08:15:00',
							day_end_time: '15:45:00',
						},
					},
				});
			}
			if (url.includes('can_view_room_utilization_analytics')) {
				const state = reactive({
					data: null as any,
					loading: false,
					async submit(payload?: any) {
						analyticsSubmitMock(payload);
						state.data = { allowed: roomUtilizationState.analyticsAllowed };
						return state.data;
					},
				});
				return state;
			}
			if (url.includes('get_staff_home_header')) {
				const state = reactive({
					data: null as any,
					loading: false,
					async submit(payload?: any) {
						headerSubmitMock(payload);
						state.data = {
							capabilities: {
								quick_action_create_meeting: true,
								quick_action_create_school_event: false,
							},
						};
						return state.data;
					},
				});
				return state;
			}
			if (url.includes('get_free_rooms')) {
				const state = reactive({
					data: { rooms: [] as any[] },
					loading: false,
					async submit(payload?: any) {
						freeRoomsSubmitMock(payload);
						return state.data;
					},
				});
				return state;
			}
			if (url.includes('get_location_calendar')) {
				const state = reactive({
					data: locationCalendarState.data,
					loading: false,
					async submit() {
						state.data = locationCalendarState.data;
						return state.data;
					},
				});
				return state;
			}
			return createMockResource(auto ? {} : null);
		},
	};
});

vi.mock('@/components/analytics/StatsTile.vue', () => ({
	default: defineComponent({
		name: 'StatsTileStub',
		setup() {
			return () => h('div', { 'data-testid': 'stats-tile' });
		},
	}),
}));

vi.mock('@/components/analytics/KpiRow.vue', () => ({
	default: defineComponent({
		name: 'KpiRowStub',
		setup() {
			return () => h('div', { 'data-testid': 'kpi-row' });
		},
	}),
}));

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({
		open: overlayOpenMock,
	}),
}));

import RoomUtilization from '@/pages/staff/analytics/RoomUtilization.vue';

const cleanupFns: Array<() => void> = [];

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountRoomUtilization() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(RoomUtilization);
			},
		})
	);

	app.mount(host);
	cleanupFns.push(() => {
		app.unmount();
		host.remove();
	});
}

afterEach(() => {
	overlayOpenMock.mockReset();
	analyticsSubmitMock.mockReset();
	headerSubmitMock.mockReset();
	freeRoomsSubmitMock.mockReset();
	roomUtilizationState.analyticsAllowed = 0;
	locationCalendarState.data = {
		locations: [{ value: 'SCI-LAB', label: 'Science Lab' }],
		events: [],
		selected_location_label: null,
		note: 'Select a location or building to load its calendar.',
	};
	while (cleanupFns.length) cleanupFns.pop()?.();
	document.body.innerHTML = '';
});

describe('RoomUtilization', () => {
	it('opens the event quick create overlay with the selected school prefilled', async () => {
		mountRoomUtilization();
		await flushUi();

		const createEventButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Schedule meeting')
		);

		expect(createEventButton).toBeDefined();
		createEventButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(overlayOpenMock).toHaveBeenCalledWith('event-quick-create', {
			eventType: 'meeting',
			lockEventType: true,
			meetingMode: 'ad_hoc',
			prefillSchool: 'ISS',
		});
	});

	it('uses school portal calendar times as the default day window and shows the checkbox control', async () => {
		roomUtilizationState.analyticsAllowed = 1;

		mountRoomUtilization();
		await flushUi();

		const timeInputs = Array.from(
			document.querySelectorAll('input[type="time"]')
		) as HTMLInputElement[];
		const checkbox = document.querySelector('input[type="checkbox"]') as HTMLInputElement | null;

		expect(timeInputs.some(input => input.value === '08:15')).toBe(true);
		expect(timeInputs.some(input => input.value === '15:45')).toBe(true);
		expect(checkbox).not.toBeNull();
		expect(checkbox?.checked).toBe(false);
	});
});
