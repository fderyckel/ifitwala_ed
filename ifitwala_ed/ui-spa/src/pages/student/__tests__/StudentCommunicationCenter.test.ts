import { afterEach, describe, expect, it, vi } from 'vitest';
import { createApp, defineComponent, h, nextTick, type App } from 'vue';

const {
	getStudentCommunicationCenterMock,
	getOrgCommInteractionSummaryMock,
	getCommunicationThreadMock,
	reactToOrgCommunicationMock,
	postOrgCommunicationCommentMock,
	markOrgCommunicationReadMock,
	getOrgCommunicationItemMock,
	routerReplaceMock,
	routeState,
} = vi.hoisted(() => ({
	getStudentCommunicationCenterMock: vi.fn(),
	getOrgCommInteractionSummaryMock: vi.fn(),
	getCommunicationThreadMock: vi.fn(),
	reactToOrgCommunicationMock: vi.fn(),
	postOrgCommunicationCommentMock: vi.fn(),
	markOrgCommunicationReadMock: vi.fn(),
	getOrgCommunicationItemMock: vi.fn(),
	routerReplaceMock: vi.fn(),
	routeState: {
		query: {},
	},
}))

vi.mock('frappe-ui', () => ({
	toast: {
		success: vi.fn(),
		error: vi.fn(),
	},
}))

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
		useRoute: () => routeState,
		useRouter: () => ({
			replace: routerReplaceMock,
		}),
	};
});

vi.mock('@/components/calendar/SchoolEventModal.vue', async () => {
	const { defineComponent, h } = await import('vue');

	return {
		default: defineComponent({
			name: 'SchoolEventModalStub',
			props: {
				open: {
					type: Boolean,
					default: false,
				},
			},
			setup(props) {
				return () => (props.open ? h('div', 'School Event Modal') : null);
			},
		}),
	};
});

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
			return () => h('div', 'Interaction chips');
		},
	}),
}));

vi.mock('@/lib/services/student/studentLearningHubService', () => ({
	getStudentCommunicationCenter: getStudentCommunicationCenterMock,
}));

vi.mock('@/lib/services/communicationInteraction/communicationInteractionService', () => ({
	createCommunicationInteractionService: () => ({
		getOrgCommInteractionSummary: getOrgCommInteractionSummaryMock,
		getCommunicationThread: getCommunicationThreadMock,
		reactToOrgCommunication: reactToOrgCommunicationMock,
		postOrgCommunicationComment: postOrgCommunicationCommentMock,
		markOrgCommunicationRead: markOrgCommunicationReadMock,
	}),
}));

vi.mock('@/lib/services/orgCommunicationArchive/orgCommunicationArchiveService', () => ({
	createOrgCommunicationArchiveService: () => ({
		getOrgCommunicationItem: getOrgCommunicationItemMock,
	}),
}));

import StudentCommunicationCenter from '@/pages/student/StudentCommunicationCenter.vue';

const cleanupFns: Array<() => void> = [];

function buildCommunicationAttachment(overrides: Record<string, unknown> = {}) {
	return {
		id: 'ATT-1',
		surface: 'org_communication.attachment',
		item_id: 'ATT-1',
		owner_doctype: 'Org Communication',
		owner_name: 'COMM-1',
		file_id: 'FILE-1',
		display_name: 'Attachment',
		kind: 'other',
		preview_mode: 'icon_only',
		...overrides,
	};
}

async function flushUi() {
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
	await Promise.resolve();
	await nextTick();
}

function mountStudentCommunicationCenter() {
	const host = document.createElement('div');
	document.body.appendChild(host);

	const app: App = createApp(
		defineComponent({
			render() {
				return h(StudentCommunicationCenter);
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
	getStudentCommunicationCenterMock.mockReset();
	getOrgCommInteractionSummaryMock.mockReset();
	getCommunicationThreadMock.mockReset();
	reactToOrgCommunicationMock.mockReset();
	postOrgCommunicationCommentMock.mockReset();
	markOrgCommunicationReadMock.mockReset();
	getOrgCommunicationItemMock.mockReset();
	routerReplaceMock.mockReset();
	routeState.query = {};
	while (cleanupFns.length) {
		cleanupFns.pop()?.();
	}
	document.body.innerHTML = '';
});

describe('StudentCommunicationCenter', () => {
	it('marks unread student communications as read when opened', async () => {
		getStudentCommunicationCenterMock.mockResolvedValue({
			meta: {
				generated_at: '2026-04-15T09:00:00',
				source: 'all',
				course_id: null,
				student_group: null,
				item: null,
			},
			summary: {
				total_items: 1,
				source_counts: { school: 1 },
				unread_items: 1,
			},
			items: [
				{
					kind: 'org_communication',
					item_id: 'org::COMM-1',
					sort_at: '2026-04-14T08:00:00',
					source_type: 'school',
					source_label: 'School Update',
					context_label: 'School One',
					href: null,
					href_label: null,
					is_unread: true,
					org_communication: {
						name: 'COMM-1',
						title: 'Whole-school reminder',
						communication_type: 'Reminder',
						status: 'Published',
						priority: 'Normal',
						portal_surface: 'Portal Feed',
						school: 'School One',
						organization: 'ORG-1',
						publish_from: '2026-04-14T08:00:00',
						publish_to: null,
						brief_start_date: null,
						brief_end_date: null,
						interaction_mode: 'Student Q&A',
						allow_private_notes: 0,
						allow_public_thread: 1,
						snippet: 'Bring the signed form tomorrow.',
						has_active_thread: true,
					},
				},
			],
			total_count: 1,
			has_more: false,
			start: 0,
			page_length: 24,
		});
		getOrgCommInteractionSummaryMock.mockResolvedValue({
			'COMM-1': {
				counts: {},
				reaction_counts: {},
				reactions_total: 0,
				comments_total: 2,
				self: null,
			},
		});
		getOrgCommunicationItemMock.mockResolvedValue({
			name: 'COMM-1',
			title: 'Whole-school reminder',
			message_html: '<p>Full body</p>',
			communication_type: 'Reminder',
			priority: 'Normal',
			publish_from: '2026-04-14T08:00:00',
			attachments: [],
		});
		markOrgCommunicationReadMock.mockResolvedValue({
			ok: true,
			org_communication: 'COMM-1',
			read_at: '2026-04-15T09:05:00',
		});

		mountStudentCommunicationCenter();
		await flushUi();

		expect(getStudentCommunicationCenterMock).toHaveBeenCalledWith({
			source: 'all',
			course_id: undefined,
			student_group: undefined,
			item: undefined,
			start: 0,
			page_length: 24,
		});
		expect(document.body.textContent || '').toContain('Unread 1');
		expect(document.body.textContent || '').toContain('Whole-school reminder');
		expect(document.body.textContent || '').toContain('Unread');

		const readButton = Array.from(document.querySelectorAll('button')).find(button =>
			button.textContent?.includes('Read update')
		) as HTMLButtonElement | undefined;
		expect(readButton).toBeTruthy();
		readButton?.click();
		await flushUi();

		expect(getOrgCommunicationItemMock).toHaveBeenCalledWith({ name: 'COMM-1' });
		expect(markOrgCommunicationReadMock).toHaveBeenCalledWith({ org_communication: 'COMM-1' });
		expect(document.body.textContent || '').toContain('Seen');
		expect(document.body.textContent || '').toContain('Full body');
	});

	it('renders governed communication attachment previews for student portal detail views', async () => {
		getStudentCommunicationCenterMock.mockResolvedValue({
			meta: {
				generated_at: '2026-04-15T09:00:00',
				source: 'all',
				course_id: null,
				student_group: null,
				item: null,
			},
			summary: {
				total_items: 1,
				source_counts: { school: 1 },
				unread_items: 1,
			},
			items: [
				{
					kind: 'org_communication',
					item_id: 'org::COMM-1',
					sort_at: '2026-04-14T08:00:00',
					source_type: 'school',
					source_label: 'School Update',
					context_label: 'School One',
					href: null,
					href_label: null,
					is_unread: true,
					org_communication: {
						name: 'COMM-1',
						title: 'Whole-school reminder',
						communication_type: 'Reminder',
						status: 'Published',
						priority: 'Normal',
						portal_surface: 'Portal Feed',
						school: 'School One',
						organization: 'ORG-1',
						publish_from: '2026-04-14T08:00:00',
						publish_to: null,
						brief_start_date: null,
						brief_end_date: null,
						interaction_mode: 'Student Q&A',
						allow_private_notes: 0,
						allow_public_thread: 1,
						snippet: 'Bring the signed form tomorrow.',
						has_active_thread: true,
					},
				},
			],
			total_count: 1,
			has_more: false,
			start: 0,
			page_length: 24,
		});
		getOrgCommInteractionSummaryMock.mockResolvedValue({
			'COMM-1': {
				counts: {},
				reaction_counts: {},
				reactions_total: 0,
				comments_total: 0,
				self: null,
			},
		});
		getOrgCommunicationItemMock.mockResolvedValue({
			name: 'COMM-1',
			title: 'Whole-school reminder',
			message_html: '<p>Full body</p>',
			communication_type: 'Reminder',
			priority: 'Normal',
			publish_from: '2026-04-14T08:00:00',
			attachments: [
				{
					row_name: 'ATT-IMAGE',
					kind: 'file',
					title: 'Poster',
					file_name: 'poster.webp',
					file_size: 3072,
					attachment: buildCommunicationAttachment({
						item_id: 'ATT-IMAGE',
						display_name: 'Poster',
						kind: 'image',
						extension: 'webp',
						preview_mode: 'thumbnail_image',
						thumbnail_url:
							'/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?row_name=ATT-IMAGE',
						preview_url:
							'/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?row_name=ATT-IMAGE',
						open_url:
							'/api/method/ifitwala_ed.api.file_access.open_org_communication_attachment?row_name=ATT-IMAGE',
					}),
				},
				{
					row_name: 'ATT-LINK',
					kind: 'link',
					title: 'Course site',
					external_url: 'https://example.com/course',
					attachment: buildCommunicationAttachment({
						item_id: 'ATT-LINK',
						display_name: 'Course site',
						kind: 'link',
						preview_mode: 'external_link',
						link_url: 'https://example.com/course',
						open_url: 'https://example.com/course',
					}),
				},
			],
		});
		markOrgCommunicationReadMock.mockResolvedValue({
			ok: true,
			org_communication: 'COMM-1',
			read_at: '2026-04-15T09:05:00',
		});

		mountStudentCommunicationCenter();
		await flushUi();

		const readButton = Array.from(document.querySelectorAll('button')).find(button =>
			button.textContent?.includes('Read update')
		) as HTMLButtonElement | undefined;
		expect(readButton).toBeTruthy();
		readButton?.click();
		await flushUi();

		const imagePreview = document.querySelector('[data-communication-attachment-kind="image"] img');
		expect(imagePreview?.getAttribute('src')).toContain('ATT-IMAGE');
		expect(document.body.textContent || '').toContain('Course site');
		expect(document.body.textContent || '').toContain('Open link');
	});
});
