import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const {
	createResourceMock,
	widgetsPayloadRef,
	getOrgCommInteractionSummaryMock,
	subscribeMock,
} = vi.hoisted(() => ({
		createResourceMock: vi.fn(),
		widgetsPayloadRef: {
			current: null as Record<string, unknown> | null,
		},
		getOrgCommInteractionSummaryMock: vi.fn(),
		subscribeMock: vi.fn(() => vi.fn()),
	}));

vi.mock('frappe-ui', async () => {
	const { defineComponent, h } = await import('vue');

	createResourceMock.mockImplementation((config: { url?: string; auto?: boolean }) => {
		if (config.url === 'ifitwala_ed.api.morning_brief.get_briefing_widgets') {
			return {
				data: widgetsPayloadRef.current,
				loading: false,
				reload: vi.fn(),
			};
		}

		return {
			data: [],
			loading: false,
			reload: vi.fn(),
		};
	});

	return {
		createResource: createResourceMock,
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
		toast: vi.fn(),
	};
});

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({
		open: vi.fn(),
	}),
}));

vi.mock('@/lib/services/communicationInteraction/communicationInteractionService', () => ({
	createCommunicationInteractionService: () => ({
		getOrgCommInteractionSummary: getOrgCommInteractionSummaryMock,
		getCommunicationThread: vi.fn(),
		reactToOrgCommunication: vi.fn(),
		postOrgCommunicationComment: vi.fn(),
	}),
}));

vi.mock('@/lib/uiSignals', () => ({
	uiSignals: {
		subscribe: subscribeMock,
	},
	SIGNAL_ORG_COMMUNICATION_INVALIDATE: 'org_communication:invalidate',
}));

vi.mock('@/components/ContentDialog.vue', () => ({
	default: defineComponent({
		name: 'ContentDialogStub',
		setup() {
			return () => null;
		},
	}),
}));

vi.mock('@/components/analytics/GenericListDialog.vue', () => ({
	default: defineComponent({
		name: 'GenericListDialogStub',
		setup(_, { slots }) {
			return () => h('div', slots.default?.());
		},
	}),
}));

vi.mock('@/components/analytics/HistoryDialog.vue', () => ({
	default: defineComponent({
		name: 'HistoryDialogStub',
		setup() {
			return () => null;
		},
	}),
}));

vi.mock('@/components/CommentThreadDrawer.vue', () => ({
	default: defineComponent({
		name: 'CommentThreadDrawerStub',
		props: {
			open: {
				type: Boolean,
				default: false,
			},
		},
		setup(props) {
			return () => (props.open ? h('div', 'Comment drawer') : null);
		},
	}),
}));

vi.mock('@/components/filters/DateRangePills.vue', () => ({
	default: defineComponent({
		name: 'DateRangePillsStub',
		setup() {
			return () => h('div', 'DateRangePills');
		},
	}),
}));

vi.mock('@/pages/staff/morning_brief/components/AttendanceTrend.vue', () => ({
	default: defineComponent({
		name: 'AttendanceTrendStub',
		setup() {
			return () => h('div', 'AttendanceTrend');
		},
	}),
}));

vi.mock('@/pages/staff/morning_brief/components/AbsentStudentList.vue', () => ({
	default: defineComponent({
		name: 'AbsentStudentListStub',
		setup() {
			return () => h('div', 'AbsentStudentList');
		},
	}),
}));

import MorningBriefing from '@/pages/staff/morning_brief/MorningBriefing.vue';

const cleanupFns: Array<() => void> = [];

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function buildAnnouncement(allowPublicThread: string | boolean | number) {
	return {
		name: 'COMM-0001',
		title: 'High priority update',
		content: '<p>Shared update body</p>',
		type: 'Information',
		priority: 'High',
		interaction_mode: 'Staff Comments',
		allow_public_thread: allowPublicThread,
		allow_private_notes: 0,
	};
}

function mountMorningBriefing() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(MorningBriefing);
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
	createResourceMock.mockClear();
	widgetsPayloadRef.current = null;
	getOrgCommInteractionSummaryMock.mockReset();
	subscribeMock.mockClear();
	while (cleanupFns.length) {
		cleanupFns.pop()?.();
	}
	document.body.innerHTML = '';
});

describe('MorningBriefing', () => {
	it('shows the comments action when the announcement allows shared thread entries', async () => {
		widgetsPayloadRef.current = {
			announcements: [buildAnnouncement('true')],
			today_label: 'Monday',
		};
		getOrgCommInteractionSummaryMock.mockResolvedValue({
			'COMM-0001': {
				counts: {},
				self: null,
				reaction_counts: {},
				reactions_total: 1,
				comments_total: 2,
			},
		});

		mountMorningBriefing();
		await flushUi();

		const buttons = Array.from(document.querySelectorAll('button'));
		expect(buttons.some(button => (button.textContent || '').includes('Reactions'))).toBe(true);
		expect(buttons.some(button => (button.textContent || '').includes('Comments'))).toBe(true);
	});

	it('keeps reactions visible while hiding comments when the shared thread is off', async () => {
		widgetsPayloadRef.current = {
			announcements: [buildAnnouncement('false')],
			today_label: 'Monday',
		};
		getOrgCommInteractionSummaryMock.mockResolvedValue({
			'COMM-0001': {
				counts: {},
				self: null,
				reaction_counts: {},
				reactions_total: 1,
				comments_total: 0,
			},
		});

		mountMorningBriefing();
		await flushUi();

		const buttons = Array.from(document.querySelectorAll('button'));
		expect(buttons.some(button => (button.textContent || '').includes('Reactions'))).toBe(true);
		expect(buttons.some(button => (button.textContent || '').includes('Comments'))).toBe(false);
	});
});
