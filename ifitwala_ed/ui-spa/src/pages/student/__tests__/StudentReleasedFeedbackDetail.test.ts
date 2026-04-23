import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const {
	getStudentReleasedFeedbackDetailMock,
	exportStudentReleasedFeedbackPdfMock,
	saveStudentFeedbackReplyMock,
	saveStudentFeedbackThreadStateMock,
	toastSuccessMock,
	toastErrorMock,
	openMock,
} = vi.hoisted(() => ({
	getStudentReleasedFeedbackDetailMock: vi.fn(),
	exportStudentReleasedFeedbackPdfMock: vi.fn(),
	saveStudentFeedbackReplyMock: vi.fn(),
	saveStudentFeedbackThreadStateMock: vi.fn(),
	toastSuccessMock: vi.fn(),
	toastErrorMock: vi.fn(),
	openMock: vi.fn(),
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

vi.mock('frappe-ui', () => ({
	toast: {
		success: toastSuccessMock,
		error: toastErrorMock,
	},
}))

vi.mock('@/components/assessment/ReleasedFeedbackNavigator.vue', async () => {
	const { defineComponent, h } = await import('vue')

	return {
		default: defineComponent({
			name: 'ReleasedFeedbackNavigatorStub',
			props: {
				detail: {
					type: Object,
					required: true,
				},
				mode: {
					type: String,
					required: true,
				},
				exportBusy: {
					type: Boolean,
					required: false,
					default: false,
				},
			},
			emits: ['export-feedback-pdf'],
			setup(props, { emit }) {
				return () =>
					h('div', [
						h('div', { 'data-mode': props.mode }, (props.detail as any).context?.title || ''),
						h(
							'button',
							{
								type: 'button',
								disabled: props.exportBusy,
								onClick: () => emit('export-feedback-pdf'),
							},
							props.exportBusy ? 'Preparing…' : 'Download feedback PDF'
						),
					])
			},
		}),
	}
})

vi.mock('@/lib/services/assessment/releasedFeedbackService', () => ({
	getStudentReleasedFeedbackDetail: getStudentReleasedFeedbackDetailMock,
	exportStudentReleasedFeedbackPdf: exportStudentReleasedFeedbackPdfMock,
	saveStudentFeedbackReply: saveStudentFeedbackReplyMock,
	saveStudentFeedbackThreadState: saveStudentFeedbackThreadStateMock,
}))

import StudentReleasedFeedbackDetail from '@/pages/student/StudentReleasedFeedbackDetail.vue'

const cleanupFns: Array<() => void> = []

function buildDetail(overrides: Record<string, unknown> = {}) {
	return {
		outcome_id: 'OUT-1',
		audience: 'student',
		context: {
			title: 'Source Analysis Draft',
			course_name: 'English',
		},
		task_submission: 'TSU-1',
		grade_visible: false,
		feedback_visible: true,
		publication: {
			feedback_visibility: 'student',
			grade_visibility: 'hidden',
			derived_from_legacy_outcome: false,
			legacy_outcome_published: false,
		},
		official: {
			score: null,
			grade: null,
			grade_value: null,
			feedback: null,
		},
		feedback: {
			task_submission: 'TSU-1',
			submission_version: 2,
			summary: {
				overall: 'Strong use of evidence.',
				strengths: 'Clear thesis.',
				improvements: 'Tighten the conclusion.',
				next_steps: 'Revise the final paragraph.',
			},
			priorities: [],
			items: [],
			rubric_snapshot: [],
			threads: [],
		},
		document: null,
		allowed_actions: {
			can_reply: true,
			can_set_learner_state: true,
			can_view_threads: true,
		},
		...overrides,
	}
}

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountPage() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(StudentReleasedFeedbackDetail, {
					course_id: 'COURSE-1',
					task_outcome: 'OUT-1',
					student_group: 'GROUP-1',
					unit_plan: 'UNIT-1',
					class_session: 'SESSION-1',
					task_delivery: 'TDL-1',
				})
			},
		})
	)

	app.mount(host)
	cleanupFns.push(() => {
		app.unmount()
		host.remove()
	})

	return host
}

afterEach(() => {
	getStudentReleasedFeedbackDetailMock.mockReset()
	exportStudentReleasedFeedbackPdfMock.mockReset()
	saveStudentFeedbackReplyMock.mockReset()
	saveStudentFeedbackThreadStateMock.mockReset()
	toastSuccessMock.mockReset()
	toastErrorMock.mockReset()
	openMock.mockReset()
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

Object.defineProperty(window, 'open', {
	configurable: true,
	value: openMock,
})

describe('StudentReleasedFeedbackDetail', () => {
	it('loads the student released feedback navigator', async () => {
		getStudentReleasedFeedbackDetailMock.mockResolvedValue(buildDetail())

		const host = mountPage()
		await flushUi()

		expect(getStudentReleasedFeedbackDetailMock).toHaveBeenCalledWith({ outcome_id: 'OUT-1' })
		expect(host.textContent).toContain('Source Analysis Draft')
		expect(host.querySelector('[data-mode="student"]')).not.toBeNull()
	})

	it('exports the released feedback PDF from the student navigator', async () => {
		getStudentReleasedFeedbackDetailMock.mockResolvedValue(buildDetail())
		exportStudentReleasedFeedbackPdfMock.mockResolvedValue({
			artifact: {
				file_id: 'FILE-1',
				file_name: 'released-feedback.pdf',
				task_submission: 'TSU-1',
				submission_version: 2,
				preview_status: 'ready',
				open_url: '/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-1',
				preview_url: '/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-1',
				attachment_preview: null,
			},
		})

		const host = mountPage()
		await flushUi()

		const button = Array.from(host.querySelectorAll('button')).find(element =>
			element.textContent?.includes('Download feedback PDF')
		) as HTMLButtonElement | undefined

		expect(button).toBeTruthy()
		button?.click()
		await flushUi()

		expect(exportStudentReleasedFeedbackPdfMock).toHaveBeenCalledWith({ outcome_id: 'OUT-1' })
		expect(openMock).toHaveBeenCalledWith(
			'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-1',
			'_blank',
			'noopener,noreferrer'
		)
		expect(toastSuccessMock).toHaveBeenCalledWith('Feedback PDF prepared.')
	})
})
