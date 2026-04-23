import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const {
	createResourceMock,
	widgetsPayloadRef,
	getOrgCommInteractionSummaryMock,
	getCommunicationThreadMock,
	getOrgCommunicationItemMock,
	markOrgCommunicationReadMock,
	subscribeMock,
} = vi.hoisted(() => ({
		createResourceMock: vi.fn(),
		widgetsPayloadRef: {
			current: null as Record<string, unknown> | null,
		},
		getOrgCommInteractionSummaryMock: vi.fn(),
		getCommunicationThreadMock: vi.fn(),
		getOrgCommunicationItemMock: vi.fn(),
		markOrgCommunicationReadMock: vi.fn(),
		subscribeMock: vi.fn(() => vi.fn()),
	}));

vi.mock('frappe-ui', async () => {
	const { defineComponent, h, reactive } = await import('vue');

	createResourceMock.mockImplementation((config: { url?: string; auto?: boolean }) => {
		if (config.url === 'ifitwala_ed.api.morning_brief.get_briefing_widgets') {
			return reactive({
				data: widgetsPayloadRef.current,
				loading: false,
				reload: vi.fn(),
			});
		}

		return reactive({
			data: [],
			loading: false,
			reload: vi.fn(),
		});
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
		getCommunicationThread: getCommunicationThreadMock,
		reactToOrgCommunication: vi.fn(),
		postOrgCommunicationComment: vi.fn(),
		markOrgCommunicationRead: markOrgCommunicationReadMock,
	}),
}));

vi.mock('@/lib/services/orgCommunicationArchive/orgCommunicationArchiveService', () => ({
	createOrgCommunicationArchiveService: () => ({
		getOrgCommunicationItem: getOrgCommunicationItemMock,
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
		props: {
			modelValue: {
				type: Boolean,
				default: false,
			},
			title: {
				type: String,
				default: '',
			},
			content: {
				type: String,
				default: '',
			},
			attachments: {
				type: Array,
				default: () => [],
			},
			attachmentsLoading: {
				type: Boolean,
				default: false,
			},
			attachmentsError: {
				type: String,
				default: '',
			},
			showComments: {
				type: Boolean,
				default: true,
			},
		},
		emits: ['open-comments'],
		setup(props, { emit }) {
			return () =>
				props.modelValue
					? h('div', { 'data-testid': 'content-dialog-stub' }, [
							h('div', { 'data-testid': 'content-dialog-title' }, props.title),
							h('div', { 'data-testid': 'content-dialog-content', innerHTML: props.content }),
							h(
								'div',
								{ 'data-testid': 'content-dialog-attachments-count' },
								String((props.attachments || []).length)
							),
							h(
								'div',
								{ 'data-testid': 'content-dialog-attachments-loading' },
								String(props.attachmentsLoading)
							),
							h(
								'div',
								{ 'data-testid': 'content-dialog-attachments-error' },
								props.attachmentsError
							),
							props.showComments
								? h(
										'button',
										{
											'data-testid': 'content-dialog-open-comments',
											onClick: () => emit('open-comments'),
										},
										'Comments'
									)
								: null,
						])
					: null;
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
			return () => (props.open ? h('div', { 'data-testid': 'comment-drawer-stub' }, 'Comment drawer') : null);
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

function buildAnnouncement(options?: {
	name?: string;
	title?: string;
	allowPublicThread?: string | boolean | number;
	interactionMode?: string;
	briefStartDate?: string;
	isUnread?: boolean;
}) {
	return {
		name: options?.name || 'COMM-0001',
		title: options?.title || 'High priority update',
		content: '<p>Shared update body</p>',
		type: 'Information',
		priority: 'High',
		brief_start_date: options?.briefStartDate || '2026-04-19',
		is_unread: options?.isUnread ?? true,
		interaction_mode: options?.interactionMode || 'Staff Comments',
		allow_public_thread: options?.allowPublicThread ?? 0,
		allow_private_notes: 0,
	};
}

function clickButtonWithText(text: string) {
	const button = Array.from(document.querySelectorAll('button')).find(button =>
		(button.textContent || '').includes(text)
	);
	button?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
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
	getCommunicationThreadMock.mockReset();
	getOrgCommunicationItemMock.mockReset();
	markOrgCommunicationReadMock.mockReset();
	subscribeMock.mockClear();
	while (cleanupFns.length) {
		cleanupFns.pop()?.();
	}
	document.body.innerHTML = '';
});

describe('MorningBriefing', () => {
	it('keeps list cards focused on acknowledge and open update actions', async () => {
		widgetsPayloadRef.current = {
			announcements: [buildAnnouncement({ allowPublicThread: 'false' })],
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
		expect(buttons.some(button => (button.textContent || '').includes('Acknowledge'))).toBe(true);
		expect(buttons.some(button => (button.textContent || '').includes('Open update'))).toBe(true);
		expect(buttons.some(button => (button.textContent || '').includes('Comments'))).toBe(false);
	});

	it('hides briefing interaction actions when the communication mode is None', async () => {
		widgetsPayloadRef.current = {
			announcements: [buildAnnouncement({ interactionMode: 'None', allowPublicThread: 'false' })],
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
		expect(buttons.some(button => (button.textContent || '').includes('Reactions'))).toBe(false);
		expect(buttons.some(button => (button.textContent || '').includes('Comments'))).toBe(false);
	});

	it('supports unread-only filtering and keeps the payload order intact in the rendered stack', async () => {
		widgetsPayloadRef.current = {
			announcements: [
				buildAnnouncement({
					name: 'COMM-0002',
					title: 'Newest message',
					briefStartDate: '2026-04-19',
					isUnread: true,
				}),
				buildAnnouncement({
					name: 'COMM-0001',
					title: 'Older message',
					briefStartDate: '2026-04-18',
					isUnread: false,
				}),
			],
			today_label: 'Monday',
		};
		getOrgCommInteractionSummaryMock.mockResolvedValue({
			'COMM-0001': { counts: {}, self: null, reaction_counts: {}, reactions_total: 0, comments_total: 0 },
			'COMM-0002': { counts: {}, self: null, reaction_counts: {}, reactions_total: 1, comments_total: 0 },
		});

		mountMorningBriefing();
		await flushUi();

		const titles = Array.from(
			document.querySelectorAll('[data-testid="morning-announcement-title"]')
		).map(node => node.textContent || '');
		expect(titles).toEqual(['Newest message', 'Older message']);
		expect(
			document.querySelector('[data-testid="morning-announcements-unread-count"]')?.textContent || ''
		).toContain('1 unread');

		clickButtonWithText('Unread only');
		await flushUi();

		const unreadTitles = Array.from(
			document.querySelectorAll('[data-testid="morning-announcement-title"]')
		).map(node => node.textContent || '');
		expect(unreadTitles).toEqual(['Newest message']);
	});

	it('loads governed announcement attachments on demand when an announcement is opened', async () => {
		let resolveDetail: ((value: Record<string, unknown>) => void) | null = null;
		getOrgCommunicationItemMock.mockImplementation(
			() =>
				new Promise(resolve => {
					resolveDetail = resolve;
				})
		);
		widgetsPayloadRef.current = {
			announcements: [buildAnnouncement({ allowPublicThread: 'false' })],
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

		expect(getOrgCommunicationItemMock).not.toHaveBeenCalled();
		expect(markOrgCommunicationReadMock).not.toHaveBeenCalled();

		clickButtonWithText('Open update');
		await flushUi();

		expect(getOrgCommunicationItemMock).toHaveBeenCalledWith({ name: 'COMM-0001' });
		expect(markOrgCommunicationReadMock).toHaveBeenCalledWith({ org_communication: 'COMM-0001' });
		expect(
			document.querySelector('[data-testid="content-dialog-title"]')?.textContent || ''
		).toContain('High priority update');
		expect(
			document.querySelector('[data-testid="morning-announcement-status"]')?.textContent || ''
		).toContain('Read');
		expect(
			document.querySelector('[data-testid="content-dialog-attachments-loading"]')?.textContent
		).toBe('true');
		expect(
			document.querySelector('[data-testid="content-dialog-attachments-count"]')?.textContent
		).toBe('0');

		resolveDetail?.({
			name: 'COMM-0001',
			title: 'High priority update',
			message_html: '<p>Full detail body</p>',
			communication_type: 'Information',
			priority: 'High',
			publish_from: '2026-04-19 08:00:00',
			attachments: [
				{
					row_name: 'row-file',
					kind: 'file',
					title: 'Policy PDF',
					file_name: 'policy.pdf',
					preview_status: 'ready',
					thumbnail_url:
						'/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?org_communication=COMM-0001&row_name=row-file',
					preview_url:
						'/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?org_communication=COMM-0001&row_name=row-file',
					open_url:
						'/api/method/ifitwala_ed.api.file_access.open_org_communication_attachment?org_communication=COMM-0001&row_name=row-file',
				},
			],
		});
		await flushUi();

		expect(
			document.querySelector('[data-testid="content-dialog-attachments-loading"]')?.textContent
		).toBe('false');
		expect(
			document.querySelector('[data-testid="content-dialog-attachments-count"]')?.textContent
		).toBe('1');
		expect(
			document.querySelector('[data-testid="content-dialog-content"]')?.innerHTML || ''
		).toContain('Full detail body');
	});

	it('closes the content dialog before opening the comment drawer from the announcement overlay', async () => {
		getOrgCommunicationItemMock.mockResolvedValue({
			name: 'COMM-0001',
			title: 'High priority update',
			message_html: '<p>Full detail body</p>',
			communication_type: 'Information',
			priority: 'High',
			publish_from: '2026-04-19 08:00:00',
			attachments: [],
		});
		getCommunicationThreadMock.mockResolvedValue([]);
		widgetsPayloadRef.current = {
			announcements: [buildAnnouncement({ allowPublicThread: 'false' })],
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

		clickButtonWithText('Open update');
		await flushUi();

		expect(document.querySelector('[data-testid="content-dialog-stub"]')).not.toBeNull();

		document
			.querySelector('[data-testid="content-dialog-open-comments"]')
			?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
		await flushUi();

		expect(document.querySelector('[data-testid="content-dialog-stub"]')).toBeNull();
		expect(document.querySelector('[data-testid="comment-drawer-stub"]')).not.toBeNull();
		expect(getCommunicationThreadMock).toHaveBeenCalledWith({
			org_communication: 'COMM-0001',
			limit_start: 0,
			limit: 30,
		});
	});
});
