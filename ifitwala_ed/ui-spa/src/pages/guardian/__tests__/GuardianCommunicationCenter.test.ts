import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const {
	getGuardianCommunicationCenterMock,
	getOrgCommInteractionSummaryMock,
	getCommunicationThreadMock,
	reactToOrgCommunicationMock,
	postOrgCommunicationCommentMock,
	markOrgCommunicationReadMock,
	getOrgCommunicationItemMock,
} = vi.hoisted(() => ({
	getGuardianCommunicationCenterMock: vi.fn(),
	getOrgCommInteractionSummaryMock: vi.fn(),
	getCommunicationThreadMock: vi.fn(),
	reactToOrgCommunicationMock: vi.fn(),
	postOrgCommunicationCommentMock: vi.fn(),
	markOrgCommunicationReadMock: vi.fn(),
	getOrgCommunicationItemMock: vi.fn(),
}))

vi.mock('frappe-ui', () => ({
	toast: {
		success: vi.fn(),
		error: vi.fn(),
	},
}))

vi.mock('vue-router', async () => {
	const { defineComponent, h } = await import('vue')

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
				return () => h('a', {}, slots.default?.())
			},
		}),
	}
})

vi.mock('@/components/calendar/SchoolEventModal.vue', async () => {
	const { defineComponent, h } = await import('vue')

	return {
		default: defineComponent({
			name: 'SchoolEventModalStub',
			props: {
				open: {
					type: Boolean,
					default: false,
				},
				event: {
					type: Object,
					required: false,
					default: null,
				},
			},
			setup(props) {
				return () =>
					props.open
						? h('div', `School Event Modal ${props.event?.subject || ''}`.trim())
						: null
			},
		}),
	}
})

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
			return () => (props.open ? h('div', 'Comment drawer') : null)
		},
	}),
}))

vi.mock('@/components/InteractionEmojiChips.vue', () => ({
	default: defineComponent({
		name: 'InteractionEmojiChipsStub',
		setup() {
			return () => h('div', 'Interaction chips')
		},
	}),
}))

vi.mock('@/lib/services/guardianCommunication/guardianCommunicationService', () => ({
	getGuardianCommunicationCenter: getGuardianCommunicationCenterMock,
}))

vi.mock('@/lib/services/communicationInteraction/communicationInteractionService', () => ({
	createCommunicationInteractionService: () => ({
		getOrgCommInteractionSummary: getOrgCommInteractionSummaryMock,
		getCommunicationThread: getCommunicationThreadMock,
		reactToOrgCommunication: reactToOrgCommunicationMock,
		postOrgCommunicationComment: postOrgCommunicationCommentMock,
		markOrgCommunicationRead: markOrgCommunicationReadMock,
	}),
}))

vi.mock('@/lib/services/orgCommunicationArchive/orgCommunicationArchiveService', () => ({
	createOrgCommunicationArchiveService: () => ({
		getOrgCommunicationItem: getOrgCommunicationItemMock,
	}),
}))

import GuardianCommunicationCenter from '@/pages/guardian/GuardianCommunicationCenter.vue'

const cleanupFns: Array<() => void> = []

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountGuardianCommunicationCenter() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(GuardianCommunicationCenter)
			},
		})
	)

	app.mount(host)
	cleanupFns.push(() => {
		app.unmount()
		host.remove()
	})
}

afterEach(() => {
	getGuardianCommunicationCenterMock.mockReset()
	getOrgCommInteractionSummaryMock.mockReset()
	getCommunicationThreadMock.mockReset()
	reactToOrgCommunicationMock.mockReset()
	postOrgCommunicationCommentMock.mockReset()
	markOrgCommunicationReadMock.mockReset()
	getOrgCommunicationItemMock.mockReset()
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

describe('GuardianCommunicationCenter', () => {
	it('renders the family-wide communication feed and marks updates read when opened', async () => {
		getGuardianCommunicationCenterMock.mockResolvedValue({
			meta: {
				generated_at: '2026-04-15T09:00:00',
				source: 'all',
				student: null,
			},
			family: {
				children: [
					{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' },
					{ student: 'STU-2', full_name: 'Noah Example', school: 'School One' },
				],
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
					matched_children: [
						{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' },
						{ student: 'STU-2', full_name: 'Noah Example', school: 'School One' },
					],
					is_unread: true,
					org_communication: {
						name: 'COMM-1',
						title: 'Whole-school reminder',
						communication_type: 'Reminder',
						status: 'Published',
						priority: 'Normal',
						portal_surface: 'Guardian Portal',
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
		})
		getOrgCommInteractionSummaryMock.mockResolvedValue({
			'COMM-1': {
				counts: {},
				reaction_counts: {},
				reactions_total: 0,
				comments_total: 2,
				self: null,
			},
		})
		getOrgCommunicationItemMock.mockResolvedValue({
			name: 'COMM-1',
			title: 'Whole-school reminder',
			message_html: '<p>Full body</p>',
			communication_type: 'Reminder',
			priority: 'Normal',
			publish_from: '2026-04-14T08:00:00',
			attachments: [],
		})
		markOrgCommunicationReadMock.mockResolvedValue({
			ok: true,
			org_communication: 'COMM-1',
			read_at: '2026-04-15T09:05:00',
		})

		mountGuardianCommunicationCenter()
		await flushUi()

		expect(getGuardianCommunicationCenterMock).toHaveBeenCalledWith({
			source: 'all',
			student: undefined,
			start: 0,
			page_length: 24,
		})
		const text = document.body.textContent || ''
		expect(text).toContain('Communication Center')
		expect(text).toContain('Whole-school reminder')
		expect(text).toContain('Amina Example')
		expect(text).toContain('Noah Example')
		expect(text).toContain('Unread 1')

		const readButton = Array.from(document.querySelectorAll('button')).find(button =>
			button.textContent?.includes('Read update')
		) as HTMLButtonElement | undefined
		expect(readButton).toBeTruthy()
		readButton?.click()
		await flushUi()

		expect(getOrgCommunicationItemMock).toHaveBeenCalledWith({ name: 'COMM-1' })
		expect(markOrgCommunicationReadMock).toHaveBeenCalledWith({ org_communication: 'COMM-1' })
		expect(document.body.textContent || '').toContain('Seen')
		expect(document.body.textContent || '').toContain('Full body')
	})

	it('renders governed attachment preview cards inside the guardian communication detail', async () => {
		getGuardianCommunicationCenterMock.mockResolvedValue({
			meta: {
				generated_at: '2026-04-15T09:00:00',
				source: 'all',
				student: null,
			},
			family: {
				children: [{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' }],
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
					matched_children: [
						{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' },
					],
					is_unread: true,
					org_communication: {
						name: 'COMM-1',
						title: 'Whole-school reminder',
						communication_type: 'Reminder',
						status: 'Published',
						priority: 'Normal',
						portal_surface: 'Guardian Portal',
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
		})
		getOrgCommInteractionSummaryMock.mockResolvedValue({
			'COMM-1': {
				counts: {},
				reaction_counts: {},
				reactions_total: 0,
				comments_total: 0,
				self: null,
			},
		})
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
					preview_url: '/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?row_name=ATT-IMAGE',
					open_url: '/api/method/ifitwala_ed.api.file_access.open_org_communication_attachment?row_name=ATT-IMAGE',
				},
				{
					row_name: 'ATT-LINK',
					kind: 'link',
					title: 'School site',
					external_url: 'https://example.com/school',
					open_url: 'https://example.com/school',
				},
			],
		})
		markOrgCommunicationReadMock.mockResolvedValue({
			ok: true,
			org_communication: 'COMM-1',
			read_at: '2026-04-15T09:05:00',
		})

		mountGuardianCommunicationCenter()
		await flushUi()

		const readButton = Array.from(document.querySelectorAll('button')).find(button =>
			button.textContent?.includes('Read update')
		) as HTMLButtonElement | undefined
		expect(readButton).toBeTruthy()
		readButton?.click()
		await flushUi()

		const imagePreview = document.querySelector('[data-communication-attachment-kind="image"] img')
		expect(imagePreview?.getAttribute('src')).toContain('ATT-IMAGE')
		expect(document.body.textContent || '').toContain('School site')
		expect(document.body.textContent || '').toContain('Open link')
	})

	it('reloads the feed when the child filter changes', async () => {
		getGuardianCommunicationCenterMock
			.mockResolvedValueOnce({
				meta: {
					generated_at: '2026-04-15T09:00:00',
					source: 'all',
					student: null,
				},
				family: {
					children: [
						{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' },
						{ student: 'STU-2', full_name: 'Noah Example', school: 'School One' },
					],
				},
				summary: {
					total_items: 0,
					source_counts: {},
					unread_items: 0,
				},
				items: [],
				total_count: 0,
				has_more: false,
				start: 0,
				page_length: 24,
			})
			.mockResolvedValueOnce({
				meta: {
					generated_at: '2026-04-15T09:02:00',
					source: 'all',
					student: 'STU-2',
				},
				family: {
					children: [
						{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' },
						{ student: 'STU-2', full_name: 'Noah Example', school: 'School One' },
					],
				},
				summary: {
					total_items: 1,
					source_counts: { course: 1 },
					unread_items: 0,
				},
				items: [
					{
						kind: 'org_communication',
						item_id: 'org::COMM-2',
						sort_at: '2026-04-13T08:00:00',
						source_type: 'course',
						source_label: 'Class Update',
						context_label: 'Biology A',
						matched_children: [
							{ student: 'STU-2', full_name: 'Noah Example', school: 'School One' },
						],
						is_unread: false,
						org_communication: {
							name: 'COMM-2',
							title: 'Biology checkpoint',
							communication_type: 'Information',
							status: 'Published',
							priority: 'High',
							portal_surface: 'Guardian Portal',
							school: 'School One',
							organization: 'ORG-1',
							publish_from: '2026-04-13T08:00:00',
							publish_to: null,
							brief_start_date: null,
							brief_end_date: null,
							interaction_mode: 'Student Q&A',
							allow_private_notes: 0,
							allow_public_thread: 1,
							snippet: 'Study the lab notes.',
							has_active_thread: true,
						},
					},
				],
				total_count: 1,
				has_more: false,
				start: 0,
				page_length: 24,
			})
		getOrgCommInteractionSummaryMock.mockResolvedValue({})

		mountGuardianCommunicationCenter()
		await flushUi()

		const childSelect = document.querySelector('select') as HTMLSelectElement | null
		expect(childSelect).toBeTruthy()
		if (childSelect) {
			childSelect.value = 'STU-2'
			childSelect.dispatchEvent(new Event('change', { bubbles: true }))
		}
		await flushUi()

		expect(getGuardianCommunicationCenterMock).toHaveBeenNthCalledWith(2, {
			source: 'all',
			student: 'STU-2',
			start: 0,
			page_length: 24,
		})
		expect(document.body.textContent || '').toContain('Biology checkpoint')
	})

	it('renders school events in the same family feed and opens the event modal', async () => {
		getGuardianCommunicationCenterMock.mockResolvedValue({
			meta: {
				generated_at: '2026-04-16T09:00:00',
				source: 'all',
				student: null,
			},
			family: {
				children: [
					{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' },
					{ student: 'STU-2', full_name: 'Noah Example', school: 'School One' },
				],
			},
			summary: {
				total_items: 1,
				source_counts: { school: 1 },
				unread_items: 0,
			},
			items: [
				{
					kind: 'school_event',
					item_id: 'event::EVENT-1',
					sort_at: '2026-04-18T08:00:00',
					source_type: 'school',
					source_label: 'School Event',
					context_label: 'School One',
					matched_children: [
						{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' },
						{ student: 'STU-2', full_name: 'Noah Example', school: 'School One' },
					],
					school_event: {
						name: 'EVENT-1',
						subject: 'Spring Showcase',
						school: 'School One',
						location: 'Main Hall',
						event_type: 'Performance',
						event_category: 'Other',
						description: '<p>Families are welcome.</p>',
						snippet: 'Families are welcome.',
						starts_on: '2026-04-18T08:00:00',
						ends_on: '2026-04-18T10:00:00',
						all_day: 0,
					},
				},
			],
			total_count: 1,
			has_more: false,
			start: 0,
			page_length: 24,
		})
		getOrgCommInteractionSummaryMock.mockResolvedValue({})

		mountGuardianCommunicationCenter()
		await flushUi()

		const text = document.body.textContent || ''
		expect(text).toContain('Spring Showcase')
		expect(text).toContain('Amina Example')
		expect(text).toContain('Noah Example')

		const viewEventButton = Array.from(document.querySelectorAll('button')).find(button =>
			button.textContent?.includes('View event')
		) as HTMLButtonElement | undefined
		expect(viewEventButton).toBeTruthy()
		viewEventButton?.click()
		await flushUi()

		expect(document.body.textContent || '').toContain('School Event Modal Spring Showcase')
	})

	it('shows ask-school semantics for private student q-and-a updates', async () => {
		getGuardianCommunicationCenterMock.mockResolvedValue({
			meta: {
				generated_at: '2026-04-15T09:00:00',
				source: 'all',
				student: null,
			},
			family: {
				children: [{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' }],
			},
			summary: {
				total_items: 1,
				source_counts: { school: 1 },
				unread_items: 1,
			},
			items: [
				{
					kind: 'org_communication',
					item_id: 'org::COMM-PRIVATE',
					sort_at: '2026-04-14T08:00:00',
					source_type: 'school',
					source_label: 'School Update',
					context_label: 'School One',
					matched_children: [
						{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' },
					],
					is_unread: true,
					org_communication: {
						name: 'COMM-PRIVATE',
						title: 'Private follow-up',
						communication_type: 'Information',
						status: 'Published',
						priority: 'Normal',
						portal_surface: 'Guardian Portal',
						school: 'School One',
						organization: 'ORG-1',
						publish_from: '2026-04-14T08:00:00',
						publish_to: null,
						brief_start_date: null,
						brief_end_date: null,
						interaction_mode: 'Student Q&A',
						allow_private_notes: 1,
						allow_public_thread: 0,
						snippet: 'Ask the school privately.',
						has_active_thread: true,
					},
				},
			],
			total_count: 1,
			has_more: false,
			start: 0,
			page_length: 24,
		})
		getOrgCommInteractionSummaryMock.mockResolvedValue({
			'COMM-PRIVATE': {
				counts: {},
				reaction_counts: {},
				reactions_total: 0,
				comments_total: 0,
				self: null,
			},
		})

		mountGuardianCommunicationCenter()
		await flushUi()

		const text = document.body.textContent || ''
		expect(text).toContain('Ask School')
		expect(text).not.toContain('Interaction chips')
	})
})
