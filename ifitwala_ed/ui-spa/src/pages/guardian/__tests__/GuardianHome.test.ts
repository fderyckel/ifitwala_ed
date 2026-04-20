// ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianHome.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { getGuardianHomeSnapshotMock, overlayOpenMock } = vi.hoisted(() => ({
	getGuardianHomeSnapshotMock: vi.fn(),
	overlayOpenMock: vi.fn(),
}))

vi.mock('frappe-ui', async () => {
	const { defineComponent, h } = await import('vue')

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
				return () => h('span', { 'data-feather-icon': props.name })
			},
		}),
	}
})

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

vi.mock('@/lib/services/guardianHome/guardianHomeService', () => ({
	getGuardianHomeSnapshot: getGuardianHomeSnapshotMock,
}))

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({
		open: overlayOpenMock,
	}),
}))

import GuardianHome from '@/pages/guardian/GuardianHome.vue'

const cleanupFns: Array<() => void> = []

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountGuardianHome() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(GuardianHome)
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
	overlayOpenMock.mockReset()
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

describe('GuardianHome', () => {
	it('renders the Phase-1 family snapshot zones from the canonical payload', async () => {
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
			policies: {
				pending_count: 2,
				items: [
					{
						policy_version: 'VER-1',
						policy_title: 'Family Handbook',
						version_label: '2026',
						description: 'Review family expectations.',
						status_label: 'Pending acknowledgement',
						href: { name: 'guardian-policies' },
					},
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
									{
										start_time: '08:00',
										end_time: '09:00',
										title: 'Math',
										subtitle: 'Room 101',
										kind: 'course',
									},
								],
								tasks_due: [
									{
										task_delivery: 'TD-1',
										title: 'Essay draft',
										due_date: '2026-03-13',
										kind: 'homework',
										status: 'assigned',
									},
								],
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
						summary: 'Needs follow-up',
					},
				],
				preparation_and_support: [
					{
						student: 'STU-1',
						date: '2026-03-13',
						label: 'Prepare for: Essay draft',
						source: 'task',
					},
				],
				recent_activity: [
					{
						type: 'task_result',
						student: 'STU-1',
						task_outcome: 'OUT-1',
						title: 'Essay draft',
						published_on: '2026-03-12',
						published_by: 'Teacher One',
					},
				],
				learning_highlights: [
					{
						student: 'STU-1',
						student_name: 'Amina Example',
						course: 'COURSE-1',
						course_name: 'Biology',
						class_label: 'Biology A',
						unit_title: 'Cells and Systems',
						focus_statement: 'Students are comparing how cell structures work together.',
						next_step: 'Complete Cell Structure Checkpoint',
						next_step_supporting_text: 'Due 2026-03-14',
						dinner_prompt: 'Ask how this unit connects to structure and function in living systems.',
					},
				],
			},
			counts: {
				unread_communications: 2,
				unread_visible_student_logs: 1,
				upcoming_due_tasks: 3,
				upcoming_assessments: 1,
			},
		})

		mountGuardianHome()
		await flushUi()

		expect(getGuardianHomeSnapshotMock).toHaveBeenCalledWith({ school_days: 7 })
		const text = document.body.textContent || ''
		expect(text).toContain('Family Snapshot')
		expect(text).toContain('School Calendar')
		expect(text).toContain('Communications')
		expect(text).toContain('Policies need your acknowledgement')
		expect(text).toContain('Family Handbook')
		expect(text).toContain('Learning Highlights')
		expect(text).toContain('Students are comparing how cell structures work together.')
		expect(text).toContain('Talk at home')
		expect(text).toContain('View learning brief')
		expect(text).toContain('Unread communications')
		expect(text).toContain('2')
		expect(text).toContain('Family Timeline')
		expect(text).toContain('Amina Example')
		expect(text).toContain('Math')
		expect(text).toContain('Due: Essay draft')
		expect(text).toContain('Attention Needed')
		expect(text).toContain('Needs follow-up')
		expect(text).toContain('Preparation & Support')
		expect(text).toContain('Prepare for: Essay draft')
		expect(text).toContain('Recent Activity')
		expect(text).toContain('Published by Teacher One')
	})

	it('renders an explicit error state when the guardian snapshot fails to load', async () => {
		getGuardianHomeSnapshotMock.mockRejectedValue(new Error('Network failed'))

		mountGuardianHome()
		await flushUi()

		const text = document.body.textContent || ''
		expect(text).toContain('Could not load guardian home snapshot.')
		expect(text).toContain('Network failed')
	})

	it('opens the guardian calendar overlay from the quick-link grid', async () => {
		getGuardianHomeSnapshotMock.mockResolvedValue({
			meta: {
				generated_at: '2026-03-13T09:00:00',
				anchor_date: '2026-03-13',
				school_days: 7,
				guardian: { name: 'GRD-0001' },
			},
			family: {
				children: [],
			},
			policies: {
				pending_count: 0,
				items: [],
			},
			zones: {
				family_timeline: [],
				attention_needed: [],
				preparation_and_support: [],
				recent_activity: [],
				learning_highlights: [],
			},
			counts: {
				unread_communications: 0,
				unread_visible_student_logs: 0,
				upcoming_due_tasks: 0,
				upcoming_assessments: 0,
			},
		})

		mountGuardianHome()
		await flushUi()

		const calendarButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('School Calendar')
		)
		expect(calendarButton).toBeTruthy()

		calendarButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))

		expect(overlayOpenMock).toHaveBeenCalledWith('guardian-calendar', {})
	})
})
