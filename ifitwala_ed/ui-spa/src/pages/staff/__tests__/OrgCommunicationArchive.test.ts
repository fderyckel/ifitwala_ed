import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const {
	getArchiveContextMock,
	getOrgCommunicationFeedMock,
	getOrgCommunicationItemMock,
	getOrgCommInteractionSummaryMock,
	subscribeMock,
} = vi.hoisted(() => ({
	getArchiveContextMock: vi.fn(),
	getOrgCommunicationFeedMock: vi.fn(),
	getOrgCommunicationItemMock: vi.fn(),
	getOrgCommInteractionSummaryMock: vi.fn(),
	subscribeMock: vi.fn(() => vi.fn()),
}));

vi.mock('frappe-ui', async () => {
	const { defineComponent, h } = await import('vue');

	return {
		Badge: defineComponent({
			name: 'BadgeStub',
			setup(_, { slots }) {
				return () => h('span', slots.default?.());
			},
		}),
		Button: defineComponent({
			name: 'ButtonStub',
			props: {
				disabled: {
					type: Boolean,
					default: false,
				},
			},
			setup(props, { attrs, slots }) {
				return () => h('button', { ...attrs, disabled: props.disabled }, slots.default?.());
			},
		}),
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
		FormControl: defineComponent({
			name: 'FormControlStub',
			props: {
				modelValue: {
					type: [String, Number, Boolean, Object],
					default: null,
				},
				options: {
					type: Array,
					default: () => [],
				},
			},
			emits: ['update:modelValue'],
			setup(props, { emit }) {
				return () =>
					h(
						'select',
						{
							value: props.modelValue as string | number | undefined,
							onChange: (event: Event) =>
								emit('update:modelValue', (event.target as HTMLSelectElement).value),
						},
						(props.options as Array<{ label?: string; value?: string | null }>).map(option =>
							h('option', { value: option.value ?? '' }, option.label ?? '')
						)
					);
			},
		}),
		LoadingIndicator: defineComponent({
			name: 'LoadingIndicatorStub',
			setup() {
				return () => h('div', 'Loading');
			},
		}),
		toast: vi.fn(),
	};
});

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({}),
}));

vi.mock('@/lib/services/orgCommunicationArchive/orgCommunicationArchiveService', () => ({
	createOrgCommunicationArchiveService: () => ({
		getArchiveContext: getArchiveContextMock,
		getOrgCommunicationFeed: getOrgCommunicationFeedMock,
		getOrgCommunicationItem: getOrgCommunicationItemMock,
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

vi.mock('@/components/filters/FiltersBar.vue', () => ({
	default: defineComponent({
		name: 'FiltersBarStub',
		setup(_, { slots }) {
			return () => h('div', slots.default?.());
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

vi.mock('@/components/InteractionEmojiChips.vue', () => ({
	default: defineComponent({
		name: 'InteractionEmojiChipsStub',
		setup() {
			return () => h('div', { 'data-testid': 'interaction-chips-stub' }, 'Emoji');
		},
	}),
}));

import OrgCommunicationArchive from '@/pages/staff/OrgCommunicationArchive.vue';

const cleanupFns: Array<() => void> = [];

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function buildItem(options?: {
	allowPublicThread?: string | number | boolean;
	interactionMode?: string;
}) {
	return {
		name: 'COMM-0001',
		title: 'Shared update',
		communication_type: 'Information',
		status: 'Published',
		priority: 'Normal',
		portal_surface: 'Everywhere',
		school: null,
		organization: 'ORG-1',
		publish_from: '2026-04-12 08:00:00',
		publish_to: null,
		brief_start_date: null,
		brief_end_date: null,
		interaction_mode: options?.interactionMode || 'Staff Comments',
		allow_private_notes: 0,
		allow_public_thread: options?.allowPublicThread ?? 0,
		snippet: 'Short snippet',
		audience_label: 'All staff',
	};
}

function mountArchive() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(OrgCommunicationArchive);
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
	getArchiveContextMock.mockReset();
	getOrgCommunicationFeedMock.mockReset();
	getOrgCommunicationItemMock.mockReset();
	getOrgCommInteractionSummaryMock.mockReset();
	subscribeMock.mockClear();
	while (cleanupFns.length) {
		cleanupFns.pop()?.();
	}
	document.body.innerHTML = '';
});

describe('OrgCommunicationArchive', () => {
	it('keeps the comments button visible for staff comments on the staff archive surface', async () => {
		getArchiveContextMock.mockResolvedValue({
			my_teams: [],
			my_groups: [],
			schools: [],
			organizations: [],
			defaults: {
				organization: null,
				school: null,
				team: null,
			},
		});
		getOrgCommunicationFeedMock.mockResolvedValue({
			items: [buildItem({ allowPublicThread: 'false' })],
			has_more: false,
			start: 0,
			page_length: 10,
		});
		getOrgCommunicationItemMock.mockResolvedValue({
			name: 'COMM-0001',
			message_html: '<p>Body</p>',
			attachments: [],
		});
		getOrgCommInteractionSummaryMock.mockResolvedValue({
			'COMM-0001': {
				counts: {},
				self: null,
				reaction_counts: {},
				reactions_total: 1,
				comments_total: 2,
			},
		});

		mountArchive();
		await flushUi();

		const commentButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Comments')
		);

		expect(commentButton).toBeDefined();
		expect(document.body.querySelector('[data-testid="interaction-chips-stub"]')).not.toBeNull();
	});

	it('hides archive interaction actions when the communication mode is None', async () => {
		getArchiveContextMock.mockResolvedValue({
			my_teams: [],
			my_groups: [],
			schools: [],
			organizations: [],
			defaults: {
				organization: null,
				school: null,
				team: null,
			},
		});
		getOrgCommunicationFeedMock.mockResolvedValue({
			items: [buildItem({ interactionMode: 'None', allowPublicThread: 'false' })],
			has_more: false,
			start: 0,
			page_length: 10,
		});
		getOrgCommunicationItemMock.mockResolvedValue({
			name: 'COMM-0001',
			message_html: '<p>Body</p>',
			attachments: [],
		});
		getOrgCommInteractionSummaryMock.mockResolvedValue({
			'COMM-0001': {
				counts: {},
				self: null,
				reaction_counts: {},
				reactions_total: 1,
				comments_total: 0,
			},
		});

		mountArchive();
		await flushUi();

		const commentButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Comments')
		);

		expect(commentButton).toBeUndefined();
		expect(document.body.querySelector('[data-testid="interaction-chips-stub"]')).toBeNull();
	});
});
