import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const {
	openStudentQuizSessionMock,
	saveStudentQuizAttemptMock,
	submitStudentQuizAttemptMock,
} = vi.hoisted(() => ({
	openStudentQuizSessionMock: vi.fn(),
	saveStudentQuizAttemptMock: vi.fn(),
	submitStudentQuizAttemptMock: vi.fn(),
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
	}
})

vi.mock('@/lib/services/student/studentQuizService', () => ({
	openStudentQuizSession: openStudentQuizSessionMock,
	saveStudentQuizAttempt: saveStudentQuizAttemptMock,
	submitStudentQuizAttempt: submitStudentQuizAttemptMock,
}))

import StudentQuiz from '@/pages/student/StudentQuiz.vue'

const cleanupFns: Array<() => void> = []

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function buildReviewPayload(overrides: Record<string, unknown> = {}) {
	return {
		mode: 'review' as const,
		session: {
			task_delivery: 'TDL-QUIZ-1',
			task: 'TASK-QUIZ-1',
			title: 'Cell Structure Checkpoint',
			course: 'COURSE-1',
			is_practice: 0,
			attempt_id: 'QAT-1',
			attempt_number: 1,
			status: 'Submitted',
			submitted_on: '2026-04-21 09:30:00',
			score: null,
			percentage: null,
			passed: 0,
			requires_manual_review: 0,
			outcome_id: 'OUT-QUIZ-1',
		},
		review: {
			attempt: {
				attempt_id: 'QAT-1',
				attempt_number: 1,
				status: 'Submitted',
				submitted_on: '2026-04-21 09:30:00',
				score: null,
				percentage: null,
				passed: 0,
				requires_manual_review: 0,
			},
			items: [
				{
					item_id: 'QAI-1',
					position: 1,
					question_type: 'Single Choice',
					prompt_html: '<p>Pick one</p>',
					options: [{ id: 'OPT-1', text: 'A' }],
					response_text: null,
					selected_option_ids: ['OPT-1'],
					awarded_score: null,
					is_correct: 0,
					requires_manual_grading: 0,
					explanation_html: null,
					correct_option_ids: [],
					accepted_answers: [],
				},
			],
		},
		released_result: {
			outcome_id: 'OUT-QUIZ-1',
			task_submission: null,
			grade_visible: false,
			feedback_visible: false,
			publication: {
				feedback_visibility: 'hidden',
				grade_visibility: 'hidden',
				derived_from_legacy_outcome: true,
				legacy_outcome_published: false,
			},
			official: {
				score: null,
				grade: null,
				grade_value: null,
				feedback: null,
			},
			feedback: null,
		},
		...overrides,
	}
}

function mountStudentQuiz() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(StudentQuiz, {
					course_id: 'COURSE-1',
					task_delivery: 'TDL-QUIZ-1',
					student_group: 'GROUP-1',
					unit_plan: 'UNIT-PLAN-1',
					class_session: 'CLASS-SESSION-1',
				})
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
	openStudentQuizSessionMock.mockReset()
	saveStudentQuizAttemptMock.mockReset()
	submitStudentQuizAttemptMock.mockReset()
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

describe('StudentQuiz', () => {
	it('shows released grade and feedback for assessed quiz review', async () => {
		openStudentQuizSessionMock.mockResolvedValue(
			buildReviewPayload({
				session: {
					task_delivery: 'TDL-QUIZ-1',
					task: 'TASK-QUIZ-1',
					title: 'Cell Structure Checkpoint',
					course: 'COURSE-1',
					is_practice: 0,
					attempt_id: 'QAT-1',
					attempt_number: 1,
					status: 'Submitted',
					submitted_on: '2026-04-21 09:30:00',
					score: 8,
					percentage: 80,
					passed: 1,
					requires_manual_review: 0,
					outcome_id: 'OUT-QUIZ-1',
				},
				review: {
					attempt: {
						attempt_id: 'QAT-1',
						attempt_number: 1,
						status: 'Submitted',
						submitted_on: '2026-04-21 09:30:00',
						score: 8,
						percentage: 80,
						passed: 1,
						requires_manual_review: 0,
					},
					items: [
						{
							item_id: 'QAI-1',
							position: 1,
							question_type: 'Single Choice',
							prompt_html: '<p>Pick one</p>',
							options: [{ id: 'OPT-1', text: 'A' }],
							response_text: null,
							selected_option_ids: ['OPT-1'],
							awarded_score: 1,
							is_correct: 1,
							requires_manual_grading: 0,
							explanation_html: '<p>Because</p>',
							correct_option_ids: ['OPT-1'],
							accepted_answers: [],
						},
					],
				},
				released_result: {
					outcome_id: 'OUT-QUIZ-1',
					task_submission: null,
					grade_visible: true,
					feedback_visible: true,
					publication: {
						feedback_visibility: 'student',
						grade_visibility: 'student',
						derived_from_legacy_outcome: false,
						legacy_outcome_published: false,
					},
					official: {
						score: 8,
						grade: 'B',
						grade_value: 3,
						feedback: 'Strong explanation of the membrane.',
					},
					feedback: {
						task_submission: null,
						submission_version: null,
						summary: {
							overall: 'Strong explanation of the membrane.',
							strengths: 'Good use of vocabulary.',
							improvements: '',
							next_steps: 'Review osmosis before the next lesson.',
						},
						items: [],
					},
				},
			})
		)

		mountStudentQuiz()
		await flushUi()

		expect(document.body.textContent).toContain('Score 8')
		expect(document.body.textContent).toContain('80%')
		expect(document.body.textContent).toContain('Grade released')
		expect(document.body.textContent).toContain('Feedback released')
		expect(document.body.textContent).toContain('Grade B')
		expect(document.body.textContent).toContain('Strong explanation of the membrane.')
		expect(document.body.textContent).toContain('Good use of vocabulary.')
		expect(document.body.textContent).toContain('Review osmosis before the next lesson.')
		expect(document.body.textContent).toContain('Score 1.')
		expect(document.body.innerHTML).toContain('Because')
		expect(document.body.innerHTML).toContain('student-released-feedback')
	})

	it('keeps assessed quiz review redacted until release', async () => {
		openStudentQuizSessionMock.mockResolvedValue(buildReviewPayload())

		mountStudentQuiz()
		await flushUi()

		expect(document.body.textContent).toContain(
			'Results and feedback will appear here after your teacher releases them.'
		)
		expect(document.body.textContent).toContain('Response recorded.')
		expect(document.body.textContent).not.toContain('Score 8')
		expect(document.body.textContent).not.toContain('Correct.')
	})
})
