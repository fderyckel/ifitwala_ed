import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, ref, type App } from 'vue';

const {
	fetchPrefsMock,
	refreshMock,
	setRangeMock,
	setSourcesMock,
	toggleSourceMock,
	overlayOpenMock,
	subscribeMock,
	toastErrorMock,
} = vi.hoisted(() => ({
	fetchPrefsMock: vi.fn(),
	refreshMock: vi.fn(),
	setRangeMock: vi.fn(),
	setSourcesMock: vi.fn(),
	toggleSourceMock: vi.fn(),
	overlayOpenMock: vi.fn(),
	subscribeMock: vi.fn(() => vi.fn()),
	toastErrorMock: vi.fn(),
}));

vi.mock('frappe-ui', async () => {
	const { defineComponent, h } = await import('vue');

	return {
		FeatherIcon: defineComponent({
			name: 'FeatherIconStub',
			props: {
				name: {
					type: String,
					default: '',
				},
			},
			setup(props) {
				return () => h('span', { 'data-feather-icon': props.name });
			},
		}),
		toast: {
			error: toastErrorMock,
		},
	};
});

vi.mock('@fullcalendar/vue3', async () => {
	const { defineComponent, h } = await import('vue');
	return {
		default: defineComponent({
			name: 'FullCalendarStub',
			setup(_, { expose }) {
				expose({
					getApi: () => ({
						setOption: vi.fn(),
						render: vi.fn(),
						changeView: vi.fn(),
						view: { type: 'timeGridWeek' },
					}),
				});
				return () => h('div', { 'data-testid': 'full-calendar' });
			},
		}),
	};
});

vi.mock('@fullcalendar/daygrid', () => ({ default: {} }));
vi.mock('@fullcalendar/timegrid', () => ({ default: {} }));
vi.mock('@fullcalendar/list', () => ({ default: {} }));
vi.mock('@fullcalendar/core', () => ({}));

vi.mock('@/composables/useCalendarEvents', () => {
	const events = ref([]);
	const counts = ref({});
	const timezone = ref('UTC');
	const loading = ref(false);
	const error = ref<string | null>(null);
	const lastUpdated = ref<number | null>(null);
	const activeSources = ref(new Set(['student_group', 'meeting', 'school_event', 'staff_holiday']));
	const isEmpty = ref(true);

	return {
		useCalendarEvents: () => ({
			events,
			counts,
			timezone,
			loading,
			error,
			lastUpdated,
			activeSources,
			isEmpty,
			setRange: setRangeMock,
			refresh: refreshMock,
			setSources: setSourcesMock,
			toggleSource: toggleSourceMock,
		}),
	};
});

vi.mock('@/composables/useCalendarPrefs', () => ({
	useCalendarPrefs: () => ({
		fetch: fetchPrefsMock,
	}),
}));

vi.mock('@/components/calendar/scheduleCalendarListMeta', () => ({
	buildScheduleCalendarListMeta: () => '',
}));

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({
		open: overlayOpenMock,
	}),
}));

vi.mock('@/lib/uiSignals', () => ({
	uiSignals: {
		subscribe: subscribeMock,
	},
	SIGNAL_CALENDAR_INVALIDATE: 'calendar:invalidate',
}));

import ScheduleCalendar from '@/components/calendar/ScheduleCalendar.vue';

const cleanupFns: Array<() => void> = [];
let originalOpen: typeof window.open;

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountScheduleCalendar() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(ScheduleCalendar);
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
	fetchPrefsMock.mockReset();
	refreshMock.mockReset();
	setRangeMock.mockReset();
	setSourcesMock.mockReset();
	toggleSourceMock.mockReset();
	overlayOpenMock.mockReset();
	subscribeMock.mockClear();
	toastErrorMock.mockReset();
	while (cleanupFns.length) cleanupFns.pop()?.();
	document.body.innerHTML = '';
	window.open = originalOpen;
});

describe('ScheduleCalendar export action', () => {
	it('renders the staff calendar inside the taller-slot viewport wrapper', async () => {
		originalOpen = window.open;
		window.open = vi.fn() as typeof window.open;
		fetchPrefsMock.mockResolvedValue({
			weekendDays: [0, 6],
			defaultSlotMin: '07:00:00',
			defaultSlotMax: '17:00:00',
		});

		mountScheduleCalendar();
		await flushUi();

		const viewport = document.querySelector('.schedule-calendar__viewport') as HTMLElement | null;
		expect(viewport).toBeTruthy();
	});

	it('surfaces the print action in the header controls and shows the export presets', async () => {
		originalOpen = window.open;
		window.open = vi.fn() as typeof window.open;
		fetchPrefsMock.mockResolvedValue({
			weekendDays: [0, 6],
			defaultSlotMin: '07:00:00',
			defaultSlotMax: '17:00:00',
		});

		mountScheduleCalendar();
		await flushUi();

		const printButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Print timetable')
		);
		expect(printButton).toBeTruthy();

		printButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(document.body.textContent || '').toContain('Choose a timetable range');
		expect(document.body.textContent || '').toContain('This week');
		expect(document.body.textContent || '').toContain('Next 2 weeks');
		expect(document.body.textContent || '').toContain('Next month');
	});

	it('opens the dedicated timetable export url in a new tab when a preset is chosen', async () => {
		originalOpen = window.open;
		window.open = vi.fn(() => ({ closed: false } as Window)) as typeof window.open;
		fetchPrefsMock.mockResolvedValue({
			weekendDays: [0, 6],
			defaultSlotMin: '07:00:00',
			defaultSlotMax: '17:00:00',
		});

		mountScheduleCalendar();
		await flushUi();

		const printButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Print timetable')
		);
		printButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		const presetButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Next 2 weeks')
		);
		presetButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(window.open).toHaveBeenCalledWith(
			'/api/method/ifitwala_ed.api.calendar.export_staff_timetable_pdf?preset=next_2_weeks',
			'_blank',
			'noopener'
		);
		expect(document.body.textContent || '').not.toContain('Choose a timetable range');
	});

	it('shows an actionable error when the browser blocks the pdf tab', async () => {
		originalOpen = window.open;
		window.open = vi.fn(() => null) as typeof window.open;
		fetchPrefsMock.mockResolvedValue({
			weekendDays: [0, 6],
			defaultSlotMin: '07:00:00',
			defaultSlotMax: '17:00:00',
		});

		mountScheduleCalendar();
		await flushUi();

		const printButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Print timetable')
		);
		printButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		const presetButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('This week')
		);
		presetButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(toastErrorMock).toHaveBeenCalledWith('Allow pop-ups to open the timetable PDF.');
		expect(document.body.textContent || '').toContain('Allow pop-ups to open the timetable PDF.');
	});
});
