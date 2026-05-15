import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const {
	getGuardianMonitoringSnapshotMock,
	getGuardianMonitoringStudentLogsMock,
	getGuardianMonitoringPublishedResultsMock,
	markGuardianStudentLogReadMock,
} = vi.hoisted(() => ({
	getGuardianMonitoringSnapshotMock: vi.fn(),
	getGuardianMonitoringStudentLogsMock: vi.fn(),
	getGuardianMonitoringPublishedResultsMock: vi.fn(),
	markGuardianStudentLogReadMock: vi.fn(),
}))
const { routeQueryMock } = vi.hoisted(() => ({
	routeQueryMock: {} as Record<string, unknown>,
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
			setup(props, { slots }) {
				return () =>
					h('a', { 'data-to': JSON.stringify(props.to || null) }, slots.default?.())
			},
		}),
		useRoute: () => ({
			query: routeQueryMock,
		}),
	}
})

vi.mock('frappe-ui', () => ({
	toast: {
		error: vi.fn(),
	},
}))

vi.mock('@/lib/services/guardianMonitoring/guardianMonitoringService', () => ({
	getGuardianMonitoringSnapshot: getGuardianMonitoringSnapshotMock,
	getGuardianMonitoringStudentLogs: getGuardianMonitoringStudentLogsMock,
	getGuardianMonitoringPublishedResults: getGuardianMonitoringPublishedResultsMock,
	markGuardianStudentLogRead: markGuardianStudentLogReadMock,
}))

import GuardianMonitoring from '@/pages/guardian/GuardianMonitoring.vue'

const cleanupFns: Array<() => void> = []
const originalScrollIntoView = HTMLElement.prototype.scrollIntoView

function baseSnapshot() {
	return {
		meta: {
			generated_at: '2026-03-13T09:00:00',
			guardian: { name: 'GRD-0001' },
			filters: { student: '', days: 30 },
		},
		family: {
			children: [
				{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' },
				{ student: 'STU-2', full_name: 'Noah Example', school: 'School One' },
			],
		},
		counts: {
			visible_student_logs: 0,
			unread_visible_student_logs: 0,
			published_results: 0,
		},
		student_logs: {
			items: [],
			total_count: 0,
			has_more: false,
			start: 0,
			page_length: 12,
		},
		published_results: {
			items: [],
			total_count: 0,
			has_more: false,
			start: 0,
			page_length: 12,
		},
	}
}

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountGuardianMonitoring() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(GuardianMonitoring)
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
	getGuardianMonitoringSnapshotMock.mockReset()
	getGuardianMonitoringStudentLogsMock.mockReset()
	getGuardianMonitoringPublishedResultsMock.mockReset()
	markGuardianStudentLogReadMock.mockReset()
	Object.keys(routeQueryMock).forEach(key => {
		delete routeQueryMock[key]
	})
	if (originalScrollIntoView) {
		Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
			configurable: true,
			value: originalScrollIntoView,
		})
	} else {
		Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
			configurable: true,
			value: undefined,
		})
	}
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

describe('GuardianMonitoring', () => {
	it('renders paged family-wide results above logs from the canonical payload', async () => {
		const longLogSummary =
			'Needs follow-up on the science reflection and should bring the signed reading journal tomorrow so the teacher can review the full progress note with the family.'
		getGuardianMonitoringSnapshotMock.mockResolvedValue({
			...baseSnapshot(),
			counts: {
				visible_student_logs: 3,
				unread_visible_student_logs: 1,
				published_results: 2,
			},
			student_logs: {
				items: [
					{
						student_log: 'LOG-1',
						student: 'STU-1',
						student_name: 'Amina Example',
						date: '2026-03-12',
						time: '09:00',
						summary: longLogSummary,
						follow_up_status: 'Open',
						is_unread: true,
					},
				],
				total_count: 3,
				has_more: true,
				start: 0,
				page_length: 12,
			},
			published_results: {
				items: [
					{
						task_outcome: 'OUT-1',
						student: 'STU-2',
						student_name: 'Noah Example',
						title: 'Science assessment',
						published_on: '2026-03-10 08:00:00',
						published_by: 'teacher@example.com',
						score: { value: 92 },
						narrative: 'Strong progress.',
						grade_visible: true,
						feedback_visible: true,
					},
				],
				total_count: 2,
				has_more: true,
				start: 0,
				page_length: 12,
			},
		})

		mountGuardianMonitoring()
		await flushUi()

		const text = document.body.textContent || ''
		expect(getGuardianMonitoringSnapshotMock).toHaveBeenCalledWith({
			student: undefined,
			days: 30,
			page_length: 12,
			prioritize_unread: false,
		})
		expect(text).toContain('Family Monitoring')
		expect(text).toContain(
			"View your child's or children's logs and published results in one place"
		)
		expect(text).toContain(longLogSummary)
		expect(text).toContain('Science assessment')
		expect(text).toContain('Load More Results')
		expect(text).toContain('Load More Logs')
		expect(document.body.innerHTML.indexOf('Published Results')).toBeLessThan(
			document.body.innerHTML.indexOf('Student Logs')
		)
		expect(text).not.toContain('Latest student logs')
		const logCard = document.querySelector('[data-student-log="LOG-1"]')
		expect(logCard?.textContent || '').toContain('Mark as seen')
		expect(logCard?.textContent || '').not.toContain('Unread')
		expect(document.body.innerHTML).toContain('guardian-released-feedback')
	})

	it('reloads the paged snapshot when the child filter changes', async () => {
		getGuardianMonitoringSnapshotMock
			.mockResolvedValueOnce(baseSnapshot())
			.mockResolvedValueOnce({
				...baseSnapshot(),
				meta: {
					generated_at: '2026-03-13T09:01:00',
					guardian: { name: 'GRD-0001' },
					filters: { student: 'STU-2', days: 30 },
				},
				counts: {
					visible_student_logs: 1,
					unread_visible_student_logs: 0,
					published_results: 0,
				},
				student_logs: {
					items: [
						{
							student_log: 'LOG-2',
							student: 'STU-2',
							student_name: 'Noah Example',
							date: '2026-03-12',
							time: '',
							summary: 'Filtered child row',
							follow_up_status: 'Completed',
							is_unread: false,
						},
					],
					total_count: 1,
					has_more: false,
					start: 0,
					page_length: 12,
				},
			})

		mountGuardianMonitoring()
		await flushUi()

		const selects = Array.from(document.querySelectorAll('select'))
		const childSelect = selects[0] as HTMLSelectElement
		childSelect.value = 'STU-2'
		childSelect.dispatchEvent(new Event('change', { bubbles: true }))
		await flushUi()

		expect(getGuardianMonitoringSnapshotMock).toHaveBeenNthCalledWith(2, {
			student: 'STU-2',
			days: 30,
			page_length: 12,
			prioritize_unread: false,
		})
		expect(document.body.textContent || '').toContain('Filtered child row')
	})

	it('marks an unread guardian log as seen through the explicit action', async () => {
		getGuardianMonitoringSnapshotMock.mockResolvedValue({
			...baseSnapshot(),
			counts: {
				visible_student_logs: 1,
				unread_visible_student_logs: 1,
				published_results: 0,
			},
			student_logs: {
				items: [
					{
						student_log: 'LOG-1',
						student: 'STU-1',
						student_name: 'Amina Example',
						date: '2026-03-12',
						time: '09:00',
						summary: 'Needs follow-up',
						follow_up_status: 'Open',
						is_unread: true,
					},
				],
				total_count: 1,
				has_more: false,
				start: 0,
				page_length: 12,
			},
		})
		markGuardianStudentLogReadMock.mockResolvedValue({
			ok: true,
			student_log: 'LOG-1',
			read_at: '2026-03-13T09:15:00',
		})

		mountGuardianMonitoring()
		await flushUi()

		const markButton = Array.from(document.querySelectorAll('button')).find(button =>
			button.textContent?.includes('Mark as seen')
		) as HTMLButtonElement | undefined
		expect(markButton).toBeTruthy()
		markButton?.click()
		await flushUi()

		expect(markGuardianStudentLogReadMock).toHaveBeenCalledWith({ log_name: 'LOG-1' })
		expect(document.body.textContent || '').not.toContain('Mark as seen')
		expect(document.querySelector('[data-student-log="LOG-1"] button')).toBeNull()
	})

	it('loads more rows independently for results and logs', async () => {
		getGuardianMonitoringSnapshotMock.mockResolvedValue({
			...baseSnapshot(),
			counts: {
				visible_student_logs: 2,
				unread_visible_student_logs: 0,
				published_results: 2,
			},
			student_logs: {
				items: [
					{
						student_log: 'LOG-1',
						student: 'STU-1',
						student_name: 'Amina Example',
						date: '2026-03-12',
						time: '',
						summary: 'First log',
						follow_up_status: '',
						is_unread: false,
					},
				],
				total_count: 2,
				has_more: true,
				start: 0,
				page_length: 12,
			},
			published_results: {
				items: [
					{
						task_outcome: 'OUT-1',
						student: 'STU-2',
						student_name: 'Noah Example',
						title: 'First result',
						published_on: '2026-03-10 08:00:00',
						published_by: 'teacher@example.com',
						score: { value: 88 },
						narrative: '',
						grade_visible: true,
						feedback_visible: true,
					},
				],
				total_count: 2,
				has_more: true,
				start: 0,
				page_length: 12,
			},
		})
		getGuardianMonitoringStudentLogsMock.mockResolvedValue({
			items: [
				{
					student_log: 'LOG-2',
					student: 'STU-1',
					student_name: 'Amina Example',
					date: '2026-03-11',
					time: '',
					summary: 'Second log',
					follow_up_status: '',
					is_unread: false,
				},
			],
			total_count: 2,
			has_more: false,
			start: 1,
			page_length: 12,
		})
		getGuardianMonitoringPublishedResultsMock.mockResolvedValue({
			items: [
				{
					task_outcome: 'OUT-2',
					student: 'STU-2',
					student_name: 'Noah Example',
					title: 'Second result',
					published_on: '2026-03-09 08:00:00',
					published_by: 'teacher@example.com',
					score: { value: 91 },
					narrative: '',
					grade_visible: true,
					feedback_visible: true,
				},
			],
			total_count: 2,
			has_more: false,
			start: 1,
			page_length: 12,
		})

		mountGuardianMonitoring()
		await flushUi()

		const loadMoreResultsButton = Array.from(document.querySelectorAll('button')).find(button =>
			button.textContent?.includes('Load More Results')
		)
		loadMoreResultsButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		const loadMoreLogsButton = Array.from(document.querySelectorAll('button')).find(button =>
			button.textContent?.includes('Load More Logs')
		)
		loadMoreLogsButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		expect(getGuardianMonitoringPublishedResultsMock).toHaveBeenCalledWith({
			student: undefined,
			days: 30,
			start: 1,
			page_length: 12,
		})
		expect(getGuardianMonitoringStudentLogsMock).toHaveBeenCalledWith({
			student: undefined,
			days: 30,
			start: 1,
			page_length: 12,
			prioritize_unread: false,
		})
		const text = document.body.textContent || ''
		expect(text).toContain('Second result')
		expect(text).toContain('Second log')
	})

	it('prioritizes unread logs for the home handoff and scrolls the first unread row into view', async () => {
		const scrolledTargets: string[] = []
		Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
			configurable: true,
			value: function () {
				scrolledTargets.push((this as HTMLElement).dataset.studentLog || '')
			},
		})

		routeQueryMock.focus = 'unread'
		getGuardianMonitoringSnapshotMock.mockResolvedValue({
			...baseSnapshot(),
			counts: {
				visible_student_logs: 2,
				unread_visible_student_logs: 1,
				published_results: 0,
			},
			student_logs: {
				items: [
					{
						student_log: 'LOG-1',
						student: 'STU-1',
						student_name: 'Amina Example',
						date: '2026-03-12',
						time: '09:00',
						summary: 'Unread detail',
						follow_up_status: 'Open',
						is_unread: true,
					},
				],
				total_count: 2,
				has_more: true,
				start: 0,
				page_length: 12,
			},
		})

		mountGuardianMonitoring()
		await flushUi()

		expect(getGuardianMonitoringSnapshotMock).toHaveBeenCalledWith({
			student: undefined,
			days: 30,
			page_length: 12,
			prioritize_unread: true,
		})
		expect(scrolledTargets).toContain('LOG-1')
	})
})
