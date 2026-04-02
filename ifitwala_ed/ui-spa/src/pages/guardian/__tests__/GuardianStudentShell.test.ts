// ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianStudentShell.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { getGuardianStudentLearningBriefMock, routeState } = vi.hoisted(() => ({
	getGuardianStudentLearningBriefMock: vi.fn(),
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
	getGuardianStudentLearningBrief: getGuardianStudentLearningBriefMock,
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
	getGuardianStudentLearningBriefMock.mockReset()
	routeState.params.student_id = 'STU-1'
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

describe('GuardianStudentShell', () => {
	it('renders the selected child learning brief', async () => {
		getGuardianStudentLearningBriefMock.mockResolvedValue({
			meta: {
				generated_at: '2026-03-13T09:00:00',
				guardian: { name: 'GRD-0001' },
				student: 'STU-1',
			},
			student: {
				student: 'STU-1',
				full_name: 'Amina Example',
				school: 'School One',
			},
			course_briefs: [
				{
					course: 'COURSE-1',
					course_name: 'Biology',
					class_label: 'Biology A',
					current_unit: {
						unit_plan: 'UNIT-1',
						title: 'Cells and Systems',
						overview: 'Students are exploring how cells function within systems.',
						essential_understanding: 'Structure and function are linked in living systems.',
						content: 'Cells and microscopy evidence',
						skills: 'Observation and comparison',
						concepts: 'Structure and function',
					},
					current_session: {
						class_session: 'SESSION-1',
						title: 'Microscope evidence walk',
						session_date: '2026-03-15',
						learning_goal: 'Compare cell structures using microscope evidence.',
					},
					focus_statement: 'Students are comparing how cell structures work together.',
					next_step: 'Complete Cell Structure Checkpoint',
					next_step_supporting_text: 'Due 2026-03-16',
					upcoming_experiences: [
						{
							class_session: 'SESSION-1',
							title: 'Microscope evidence walk',
							session_date: '2026-03-15',
							learning_goal: 'Compare cell structures using microscope evidence.',
						},
					],
					dinner_prompt: 'Ask how this unit connects to structure and function in living systems.',
					support_resources: [
						{
							material: 'MAT-1',
							title: 'Microscope guide',
							open_url: '/files/microscope-guide.pdf',
						},
					],
				},
				{
					course: 'COURSE-2',
					course_name: 'History',
					class_label: 'History A',
					current_unit: {
						unit_plan: 'UNIT-2',
						title: 'Early Civilizations',
					},
					upcoming_experiences: [],
				},
			],
		})

		mountGuardianStudentShell()
		await flushUi()

		expect(getGuardianStudentLearningBriefMock).toHaveBeenCalledWith({ student_id: 'STU-1' })
		const text = document.body.textContent || ''
		expect(text).toContain('Amina Example')
		expect(text).toContain('Learning Now')
		expect(text).toContain('Biology')
		expect(text).toContain('Cells and Systems')
		expect(text).toContain('Microscope evidence walk')
		expect(text).toContain('Dinner discussion')
		expect(text).toContain('Microscope guide')
		expect(text).not.toContain('Noah')
	})

	it('renders an explicit blocked state when the route student is outside guardian scope', async () => {
		routeState.params.student_id = 'STU-404'
		getGuardianStudentLearningBriefMock.mockRejectedValue(
			new Error('This student is not available in your guardian scope.')
		)

		mountGuardianStudentShell()
		await flushUi()

		const text = document.body.textContent || ''
		expect(text).toContain('Could not load the learning brief.')
		expect(text).toContain('This student is not available in your guardian scope.')
	})
})
