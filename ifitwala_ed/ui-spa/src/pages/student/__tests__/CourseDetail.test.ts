// ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

import type { Response as StudentLearningSpaceResponse } from '@/types/contracts/student_learning/get_student_learning_space'

const { getStudentLearningSpaceMock, routerReplaceMock } = vi.hoisted(() => ({
	getStudentLearningSpaceMock: vi.fn(),
	routerReplaceMock: vi.fn(),
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
		useRouter: () => ({
			replace: routerReplaceMock,
		}),
	}
})

vi.mock('@/lib/services/student/studentLearningHubService', () => ({
	getStudentLearningSpace: getStudentLearningSpaceMock,
}))

import CourseDetail from '@/pages/student/CourseDetail.vue'

const cleanupFns: Array<() => void> = []

function buildPayload(): StudentLearningSpaceResponse {
	return {
		meta: {
			generated_at: '2026-03-31T10:00:00',
			course_id: 'COURSE-1',
		},
		course: {
			course: 'COURSE-1',
			course_name: 'Biology',
			course_group: 'Science',
			course_image: '/files/biology.jpg',
			description: 'Explore living systems through experiments and field observations.',
		},
		access: {
			student_group_options: [
				{ student_group: 'GROUP-1', label: 'Biology A' },
				{ student_group: 'GROUP-2', label: 'Biology B' },
			],
			resolved_student_group: 'GROUP-1',
			class_teaching_plan: 'CLASS-PLAN-00001',
			course_plan: 'COURSE-PLAN-00001',
		},
		teaching_plan: {
			source: 'class_teaching_plan',
			class_teaching_plan: 'CLASS-PLAN-00001',
			title: 'Biology A · Semester 1',
			planning_status: 'Active',
			course_plan: 'COURSE-PLAN-00001',
		},
		message: null,
		learning: {
			focus: {
				current_unit: {
					unit_plan: 'UNIT-PLAN-1',
					title: 'Cells and Systems',
				},
				current_session: {
					class_session: 'CLASS-SESSION-1',
					title: 'Microscope evidence walk',
					session_date: '2026-04-01',
					learning_goal: 'Use evidence from microscope observations to compare cell structures.',
				},
				statement: 'Use evidence from microscope observations to compare cell structures.',
			},
			next_actions: [
				{
					kind: 'quiz',
					label: 'Continue Cell Structure Checkpoint',
					supporting_text: 'In Progress',
					task_delivery: 'TDL-QUIZ-1',
					class_session: 'CLASS-SESSION-1',
					unit_plan: 'UNIT-PLAN-1',
				},
			],
			selected_context: {
				unit_plan: 'UNIT-PLAN-1',
				class_session: 'CLASS-SESSION-1',
			},
			unit_navigation: [
				{
					unit_plan: 'UNIT-PLAN-1',
					title: 'Cells and Systems',
					unit_order: 1,
					session_count: 2,
					assigned_work_count: 1,
					is_current: 1,
				},
			],
		},
		resources: {
			shared_resources: [],
			class_resources: [],
			general_assigned_work: [
				{
					task_delivery: 'TDL-QUIZ-1',
					task: 'TASK-QUIZ-1',
					title: 'Cell Structure Checkpoint',
					task_type: 'Quiz',
					unit_plan: 'UNIT-PLAN-1',
					class_session: 'CLASS-SESSION-1',
					submission_status: 'Submitted',
					quiz_state: {
						can_continue: 1,
						status_label: 'In Progress',
					},
					materials: [],
				},
			],
		},
		curriculum: {
			counts: {
				units: 1,
				sessions: 2,
				assigned_work: 1,
			},
			units: [
				{
					unit_plan: 'UNIT-PLAN-1',
					title: 'Cells and Systems',
					unit_order: 1,
					duration: '4 weeks',
					estimated_duration: '12 GLH',
					overview: 'Investigate how cell structures work together inside living systems.',
					essential_understanding: 'Structure and function are linked in living systems.',
					content: 'Cell structures and microscopy evidence',
					skills: 'Observation, note-taking, comparison',
					concepts: 'Structure, function, systems',
					shared_resources: [],
					assigned_work: [
						{
							task_delivery: 'TDL-QUIZ-1',
							task: 'TASK-QUIZ-1',
							title: 'Cell Structure Checkpoint',
							task_type: 'Quiz',
							unit_plan: 'UNIT-PLAN-1',
							class_session: 'CLASS-SESSION-1',
							submission_status: 'Submitted',
							quiz_state: {
								can_continue: 1,
								status_label: 'In Progress',
							},
							materials: [],
						},
					],
					standards: [
						{
							standard_code: 'STD-1',
							standard_description: 'Explain how specialized cells contribute to a system.',
							coverage_level: 'Introduced',
						},
					],
					sessions: [
						{
							class_session: 'CLASS-SESSION-1',
							title: 'Microscope evidence walk',
							unit_plan: 'UNIT-PLAN-1',
							session_status: 'Planned',
							session_date: '2026-04-01',
							learning_goal: 'Use evidence from microscope observations to compare cell structures.',
							resources: [],
							assigned_work: [],
							activities: [
								{
									title: 'Observation walk',
									activity_type: 'Discuss',
									estimated_minutes: 15,
									student_direction: 'Rotate through the microscope stations and record two observations.',
									resource_note: 'Bring your science notebook.',
								},
							],
						},
						{
							class_session: 'CLASS-SESSION-2',
							title: 'Lab write-up',
							unit_plan: 'UNIT-PLAN-1',
							session_status: 'Planned',
							session_date: '2026-04-03',
							resources: [],
							assigned_work: [],
							activities: [],
						},
					],
				},
			],
		},
	}
}

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountCourseDetail() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(CourseDetail, { course_id: 'COURSE-1', student_group: 'GROUP-1' })
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
	getStudentLearningSpaceMock.mockReset()
	routerReplaceMock.mockReset()
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

describe('CourseDetail', () => {
	it('renders the class-aware learning space shell', async () => {
		getStudentLearningSpaceMock.mockResolvedValue(buildPayload())

		mountCourseDetail()
		await flushUi()

		expect(getStudentLearningSpaceMock).toHaveBeenCalledWith({
			course_id: 'COURSE-1',
			student_group: 'GROUP-1',
		})

		expect(document.body.textContent).toContain('Learning Space')
		expect(document.body.textContent).toContain('Biology')
		expect(document.body.textContent).toContain('Class plan published')
		expect(document.body.textContent).toContain('Learning Focus')
		expect(document.body.textContent).toContain('What to do next')
		expect(document.body.textContent).toContain('This Unit')
		expect(document.body.textContent).toContain('Structure and function are linked in living systems.')
		expect(document.body.textContent).toContain('Microscope evidence walk')
		expect(document.body.textContent).toContain('Observation walk')
		expect(document.body.textContent).toContain('Continue Cell Structure Checkpoint')
		expect(document.body.textContent).toContain('Cell Structure Checkpoint')
		expect(document.body.textContent).not.toContain('Teacher note')

		const headerImage = document.querySelector('header img')
		expect(headerImage).toBeTruthy()
		expect(headerImage?.className).toContain('aspect-square')
	})
})
