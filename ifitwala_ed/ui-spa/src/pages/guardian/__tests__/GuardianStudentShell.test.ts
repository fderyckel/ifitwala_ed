// ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianStudentShell.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { getGuardianHomeSnapshotMock, routeState } = vi.hoisted(() => ({
	getGuardianHomeSnapshotMock: vi.fn(),
	routeState: { params: { student_id: 'STU-1' } },
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
		useRoute: () => routeState,
	}
})

vi.mock('@/lib/services/guardianHome/guardianHomeService', () => ({
	getGuardianHomeSnapshot: getGuardianHomeSnapshotMock,
}))

import GuardianStudentShell from '@/pages/guardian/GuardianStudentShell.vue'

const cleanupFns: Array<() => void> = []

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountGuardianStudentShell() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(GuardianStudentShell)
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
	getGuardianHomeSnapshotMock.mockReset()
	routeState.params.student_id = 'STU-1'
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

describe('GuardianStudentShell', () => {
	it('renders only the selected child timeline and support content', async () => {
		getGuardianHomeSnapshotMock.mockResolvedValue({
			meta: {
				generated_at: '2026-03-13T09:00:00',
				anchor_date: '2026-03-13',
				school_days: 7,
				guardian: { name: 'GRD-0001' },
			},
			family: {
				children: [
					{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' },
					{ student: 'STU-2', full_name: 'Noah Example', school: 'School One' },
				],
			},
			zones: {
				family_timeline: [
					{
						date: '2026-03-13',
						label: 'Fri 13 Mar',
						is_school_day: true,
						children: [
							{
								student: 'STU-1',
								day_summary: { start_time: '08:00', end_time: '14:00' },
								blocks: [
									{ start_time: '08:00', end_time: '09:00', title: 'Math', kind: 'course' },
								],
								tasks_due: [],
								assessments_upcoming: [],
							},
							{
								student: 'STU-2',
								day_summary: { start_time: '09:00', end_time: '15:00' },
								blocks: [
									{ start_time: '09:00', end_time: '10:00', title: 'Science', kind: 'course' },
								],
								tasks_due: [],
								assessments_upcoming: [],
							},
						],
					},
				],
				attention_needed: [
					{
						type: 'student_log',
						student: 'STU-1',
						student_log: 'LOG-1',
						date: '2026-03-13',
						summary: 'Amina follow-up',
					},
					{
						type: 'student_log',
						student: 'STU-2',
						student_log: 'LOG-2',
						date: '2026-03-13',
						summary: 'Noah follow-up',
					},
					{
						type: 'communication',
						communication: 'COMM-1',
						date: '2026-03-13',
						title: 'Family-wide communication',
						is_unread: true,
					},
				],
				preparation_and_support: [
					{
						student: 'STU-1',
						date: '2026-03-13',
						label: 'Bring recorder',
						source: 'schedule',
					},
					{
						student: 'STU-2',
						date: '2026-03-13',
						label: 'Bring lab kit',
						source: 'schedule',
					},
				],
				recent_activity: [
					{
						type: 'task_result',
						student: 'STU-1',
						task_outcome: 'OUT-1',
						title: 'Amina result',
						published_on: '2026-03-12',
					},
					{
						type: 'task_result',
						student: 'STU-2',
						task_outcome: 'OUT-2',
						title: 'Noah result',
						published_on: '2026-03-12',
					},
					{
						type: 'communication',
						communication: 'COMM-1',
						date: '2026-03-13',
						title: 'Family-wide communication',
						is_unread: true,
					},
				],
			},
			counts: {
				unread_communications: 1,
				unread_visible_student_logs: 2,
				upcoming_due_tasks: 0,
				upcoming_assessments: 0,
			},
		})

		mountGuardianStudentShell()
		await flushUi()

		const text = document.body.textContent || ''
		expect(text).toContain('Amina Example')
		expect(text).toContain('Math')
		expect(text).not.toContain('Science')
		expect(text).toContain('Amina follow-up')
		expect(text).not.toContain('Noah follow-up')
		expect(text).toContain('Bring recorder')
		expect(text).not.toContain('Bring lab kit')
		expect(text).toContain('Amina result')
		expect(text).not.toContain('Noah result')
		expect(text).not.toContain('Family-wide communication')
	})

	it('renders an explicit blocked state when the route student is outside guardian scope', async () => {
		routeState.params.student_id = 'STU-404'
		getGuardianHomeSnapshotMock.mockResolvedValue({
			meta: {
				generated_at: '2026-03-13T09:00:00',
				anchor_date: '2026-03-13',
				school_days: 7,
				guardian: { name: 'GRD-0001' },
			},
			family: {
				children: [{ student: 'STU-1', full_name: 'Amina Example', school: 'School One' }],
			},
			zones: {
				family_timeline: [],
				attention_needed: [],
				preparation_and_support: [],
				recent_activity: [],
			},
			counts: {
				unread_communications: 0,
				unread_visible_student_logs: 0,
				upcoming_due_tasks: 0,
				upcoming_assessments: 0,
			},
		})

		mountGuardianStudentShell()
		await flushUi()

		const text = document.body.textContent || ''
		expect(text).toContain('This student is not available in your guardian scope.')
	})
})
