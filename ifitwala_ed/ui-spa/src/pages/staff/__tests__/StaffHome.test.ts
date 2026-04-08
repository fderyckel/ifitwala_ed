// ifitwala_ed/ui-spa/src/pages/staff/__tests__/StaffHome.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const {
	getStaffHomeHeaderMock,
	listFocusItemsMock,
	overlayOpenMock,
	resolveStaffHomeEntryMock,
	routerPushMock,
	subscribeMock,
	toastCreateMock,
} = vi.hoisted(() => ({
	getStaffHomeHeaderMock: vi.fn(),
	listFocusItemsMock: vi.fn(),
	overlayOpenMock: vi.fn(),
	resolveStaffHomeEntryMock: vi.fn(),
	routerPushMock: vi.fn(),
	subscribeMock: vi.fn(() => vi.fn()),
	toastCreateMock: vi.fn(),
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
			create: toastCreateMock,
		},
	};
});

vi.mock('vue-router', async () => {
	const { defineComponent, h } = await import('vue');

	return {
		RouterLink: defineComponent({
			name: 'RouterLinkStub',
			props: {
				to: {
					type: [String, Object],
					required: false,
					default: '',
				},
			},
			setup(_, { slots }) {
				return () => h('a', {}, slots.default?.());
			},
		}),
		useRouter: () => ({
			push: routerPushMock,
		}),
	};
});

vi.mock('@/components/calendar/ScheduleCalendar.vue', () => ({
	default: defineComponent({
		name: 'ScheduleCalendarStub',
		setup() {
			return () => h('div', { 'data-testid': 'schedule-calendar' }, 'Schedule Calendar');
		},
	}),
}));

vi.mock('@/components/focus/FocusListCard.vue', () => ({
	default: defineComponent({
		name: 'FocusListCardStub',
		props: {
			title: { type: String, default: '' },
			meta: { type: String, default: '' },
		},
		setup(props) {
			return () => h('div', { 'data-testid': 'focus-list-card' }, `${props.title} ${props.meta}`.trim());
		},
	}),
}));

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({
		open: overlayOpenMock,
	}),
}));

vi.mock('@/lib/classHubService', () => ({
	createClassHubService: () => ({
		resolveStaffHomeEntry: resolveStaffHomeEntryMock,
	}),
}));

vi.mock('@/lib/services/staff/staffHomeService', () => ({
	getStaffHomeHeader: getStaffHomeHeaderMock,
	listFocusItems: listFocusItemsMock,
}));

vi.mock('@/lib/uiSignals', () => ({
	uiSignals: {
		subscribe: subscribeMock,
	},
	SIGNAL_FOCUS_INVALIDATE: 'focus:invalidate',
	SIGNAL_ORG_COMMUNICATION_INVALIDATE: 'org_communication:invalidate',
	SIGNAL_STUDENT_LOG_INVALIDATE: 'student_log:invalidate',
}));

import StaffHome from '@/pages/staff/StaffHome.vue';

const cleanupFns: Array<() => void> = [];

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountStaffHome() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(StaffHome);
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
	getStaffHomeHeaderMock.mockReset();
	listFocusItemsMock.mockReset();
	overlayOpenMock.mockReset();
	resolveStaffHomeEntryMock.mockReset();
	routerPushMock.mockReset();
	subscribeMock.mockClear();
	toastCreateMock.mockReset();
	while (cleanupFns.length) {
		cleanupFns.pop()?.();
	}
	document.body.innerHTML = '';
});

describe('StaffHome', () => {
	it('keeps do-now actions in the right rail and moves instructional shortcuts into the explore strip', async () => {
		getStaffHomeHeaderMock.mockResolvedValue({
			first_name: 'Kis',
			full_name: 'Kis Bangkok',
			capabilities: {
				quick_action_create_task: true,
				quick_action_create_event: true,
				quick_action_create_meeting: true,
				quick_action_create_school_event: false,
				quick_action_student_log: true,
				quick_action_org_communication: true,
				quick_action_gradebook: true,
				analytics_scheduling: true,
			},
		});
		listFocusItemsMock.mockResolvedValue([]);

		mountStaffHome();
		await flushUi();

		expect(listFocusItemsMock).toHaveBeenCalledWith({ open_only: 1, limit: 8, offset: 0 });
		expect(subscribeMock).toHaveBeenCalledTimes(3);

		const quickActions = document.querySelector('[data-testid="staff-home-quick-actions"]');
		const exploreLinks = document.querySelector('[data-testid="staff-home-explore-links"]');

		expect(quickActions?.textContent || '').toContain('Schedule meeting');
		expect(quickActions?.textContent || '').toContain('Add student log');
		expect(quickActions?.textContent || '').toContain('Create communication');
		expect(quickActions?.textContent || '').not.toContain('Create task');
		expect(quickActions?.textContent || '').not.toContain('Update Gradebook');
		expect(quickActions?.textContent || '').not.toContain('Course Plans');

		expect(exploreLinks?.textContent || '').toContain('Announcement Archive');
		expect(exploreLinks?.textContent || '').toContain('Create task');
		expect(exploreLinks?.textContent || '').toContain('Update Gradebook');
		expect(exploreLinks?.textContent || '').toContain('Course Plans');
		expect(exploreLinks?.textContent || '').toContain('Room Utilization');
		expect(document.body.textContent || '').not.toContain('View all analytics');

		const createTaskButton = Array.from(exploreLinks?.querySelectorAll('button') || []).find(button =>
			(button.textContent || '').includes('Create task')
		);
		createTaskButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(overlayOpenMock).toHaveBeenCalledWith('create-task', {
			prefillStudentGroup: null,
			prefillDueDate: null,
			prefillAvailableFrom: null,
		});
	});
});
