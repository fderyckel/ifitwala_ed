// ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianAttendance.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { getGuardianAttendanceSnapshotMock } = vi.hoisted(() => ({
	getGuardianAttendanceSnapshotMock: vi.fn(),
}))

vi.mock('@/lib/services/guardianAttendance/guardianAttendanceService', () => ({
	getGuardianAttendanceSnapshot: getGuardianAttendanceSnapshotMock,
}))

import GuardianAttendance from '@/pages/guardian/GuardianAttendance.vue'

const cleanupFns: Array<() => void> = []

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountGuardianAttendance() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(GuardianAttendance)
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
	getGuardianAttendanceSnapshotMock.mockReset()
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

describe('GuardianAttendance', () => {
	it('renders family attendance and explains a selected day', async () => {
		getGuardianAttendanceSnapshotMock.mockResolvedValue({
			meta: {
				generated_at: '2026-03-13T09:00:00',
				guardian: { name: 'GRD-0001' },
				filters: {
					student: '',
					days: 60,
					start_date: '2026-02-01',
					end_date: '2026-03-31',
				},
			},
			family: {
				children: [{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' }],
			},
			counts: {
				tracked_days: 2,
				present_days: 1,
				late_days: 1,
				absence_days: 0,
			},
			students: [
				{
					student: 'STU-1',
					student_name: 'Amina Example',
					summary: {
						tracked_days: 2,
						present_days: 1,
						late_days: 1,
						absence_days: 0,
					},
					days: [
						{
							date: '2026-03-12',
							state: 'late',
							details: [
								{
									attendance: 'ATT-1',
									time: '08:15',
									attendance_code: 'L',
									attendance_code_name: 'Late',
									whole_day: false,
									course: 'Math',
									location: null,
									remark: 'Late bus',
								},
							],
						},
						{
							date: '2026-03-13',
							state: 'present',
							details: [
								{
									attendance: 'ATT-2',
									time: '08:00',
									attendance_code: 'P',
									attendance_code_name: 'Present',
									whole_day: false,
									course: 'Science',
									location: null,
									remark: null,
								},
							],
						},
					],
				},
			],
		})

		mountGuardianAttendance()
		await flushUi()

		expect(getGuardianAttendanceSnapshotMock).toHaveBeenCalledWith({
			student: undefined,
			days: 60,
		})

		const dayButton = Array.from(document.querySelectorAll('button')).find(button =>
			button.getAttribute('aria-label')?.includes('Amina Example on 2026-03-12')
		) as HTMLButtonElement | undefined
		expect(dayButton).toBeTruthy()
		expect(dayButton?.className).toContain('bg-jacaranda/12')
		dayButton?.click()
		await flushUi()

		const text = document.body.textContent || ''
		expect(text).toContain('Family Attendance')
		expect(text).toContain('Moss')
		expect(text).toContain('Jacaranda')
		expect(text).toContain('Flame')
		expect(text).toContain('Late bus')
		expect(text).toContain('Math')
		expect(text).toContain('Late or tardy')
	})

	it('reloads the payload when the child filter changes', async () => {
		getGuardianAttendanceSnapshotMock
			.mockResolvedValueOnce({
				meta: {
					generated_at: '2026-03-13T09:00:00',
					guardian: { name: 'GRD-0001' },
					filters: {
						student: '',
						days: 60,
						start_date: '2026-02-01',
						end_date: '2026-03-31',
					},
				},
				family: {
					children: [
						{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' },
						{ student: 'STU-2', full_name: 'Noah Example', school: 'School One' },
					],
				},
				counts: {
					tracked_days: 0,
					present_days: 0,
					late_days: 0,
					absence_days: 0,
				},
				students: [],
			})
			.mockResolvedValueOnce({
				meta: {
					generated_at: '2026-03-13T09:05:00',
					guardian: { name: 'GRD-0001' },
					filters: {
						student: 'STU-2',
						days: 60,
						start_date: '2026-02-01',
						end_date: '2026-03-31',
					},
				},
				family: {
					children: [
						{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' },
						{ student: 'STU-2', full_name: 'Noah Example', school: 'School One' },
					],
				},
				counts: {
					tracked_days: 1,
					present_days: 0,
					late_days: 0,
					absence_days: 1,
				},
				students: [
					{
						student: 'STU-2',
						student_name: 'Noah Example',
						summary: {
							tracked_days: 1,
							present_days: 0,
							late_days: 0,
							absence_days: 1,
						},
						days: [
							{
								date: '2026-03-11',
								state: 'absence',
								details: [
									{
										attendance: 'ATT-9',
										time: null,
										attendance_code: 'A',
										attendance_code_name: 'Absent',
										whole_day: true,
										course: null,
										location: 'Nurse',
										remark: 'Sent to nurse',
									},
								],
							},
						],
					},
				],
			})

		mountGuardianAttendance()
		await flushUi()

		const childSelect = document.querySelector('select') as HTMLSelectElement
		childSelect.value = 'STU-2'
		childSelect.dispatchEvent(new Event('change', { bubbles: true }))
		await flushUi()

		expect(getGuardianAttendanceSnapshotMock).toHaveBeenNthCalledWith(2, {
			student: 'STU-2',
			days: 60,
		})
		expect(document.body.textContent || '').toContain('Noah Example')
		expect(document.body.textContent || '').toContain('Absent')
	})
})
