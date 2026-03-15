// ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianMonitoring.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { getGuardianMonitoringSnapshotMock, markGuardianStudentLogReadMock } = vi.hoisted(() => ({
	getGuardianMonitoringSnapshotMock: vi.fn(),
	markGuardianStudentLogReadMock: vi.fn(),
}))

vi.mock('frappe-ui', () => ({
	toast: {
		error: vi.fn(),
	},
}))

vi.mock('@/lib/services/guardianMonitoring/guardianMonitoringService', () => ({
	getGuardianMonitoringSnapshot: getGuardianMonitoringSnapshotMock,
	markGuardianStudentLogRead: markGuardianStudentLogReadMock,
}))

import GuardianMonitoring from '@/pages/guardian/GuardianMonitoring.vue'

const cleanupFns: Array<() => void> = []

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
	markGuardianStudentLogReadMock.mockReset()
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

describe('GuardianMonitoring', () => {
	it('renders family-wide logs and published results from the canonical payload', async () => {
		getGuardianMonitoringSnapshotMock.mockResolvedValue({
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
				visible_student_logs: 1,
				unread_visible_student_logs: 1,
				published_results: 1,
			},
			student_logs: [
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
			published_results: [
				{
					task_outcome: 'OUT-1',
					student: 'STU-2',
					student_name: 'Noah Example',
					title: 'Science assessment',
					published_on: '2026-03-10 08:00:00',
					published_by: 'teacher@example.com',
					score: { value: 92 },
					narrative: 'Strong progress.',
				},
			],
		})

		mountGuardianMonitoring()
		await flushUi()

		const text = document.body.textContent || ''
		expect(getGuardianMonitoringSnapshotMock).toHaveBeenCalledWith({ student: undefined, days: 30 })
		expect(text).toContain('Family Monitoring')
		expect(text).toContain(
			"View your child's or children's logs and published results in one place"
		)
		expect(text).toContain('Needs follow-up')
		expect(text).toContain('Science assessment')
		expect(text).toContain('92')
	})

	it('reloads the payload when the child filter changes', async () => {
		getGuardianMonitoringSnapshotMock
			.mockResolvedValueOnce({
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
				student_logs: [],
				published_results: [],
			})
			.mockResolvedValueOnce({
				meta: {
					generated_at: '2026-03-13T09:01:00',
					guardian: { name: 'GRD-0001' },
					filters: { student: 'STU-2', days: 30 },
				},
				family: {
					children: [
						{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' },
						{ student: 'STU-2', full_name: 'Noah Example', school: 'School One' },
					],
				},
				counts: {
					visible_student_logs: 1,
					unread_visible_student_logs: 0,
					published_results: 0,
				},
				student_logs: [
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
				published_results: [],
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
		})
		expect(document.body.textContent || '').toContain('Filtered child row')
	})

	it('marks an unread guardian log as seen through the explicit action', async () => {
		getGuardianMonitoringSnapshotMock.mockResolvedValue({
			meta: {
				generated_at: '2026-03-13T09:00:00',
				guardian: { name: 'GRD-0001' },
				filters: { student: '', days: 30 },
			},
			family: {
				children: [{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' }],
			},
			counts: {
				visible_student_logs: 1,
				unread_visible_student_logs: 1,
				published_results: 0,
			},
			student_logs: [
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
			published_results: [],
		})
		markGuardianStudentLogReadMock.mockResolvedValue({
			ok: true,
			student_log: 'LOG-1',
			read_at: '2026-03-13T09:15:00',
		})

		mountGuardianMonitoring()
		await flushUi()

		const markButton = Array.from(document.querySelectorAll('button')).find(
			button => button.textContent?.includes('Mark as seen')
		) as HTMLButtonElement | undefined
		expect(markButton).toBeTruthy()
		markButton?.click()
		await flushUi()

		expect(markGuardianStudentLogReadMock).toHaveBeenCalledWith({ log_name: 'LOG-1' })
		const text = document.body.textContent || ''
		expect(text).toContain('Seen')
		expect(text).not.toContain('Mark as seen')
	})
})
