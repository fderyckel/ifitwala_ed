// ifitwala_ed/ui-spa/src/pages/student/__tests__/CourseDetail.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

import type {
	Response as StudentLearningSpaceResponse,
	StudentAssignedWork,
} from '@/types/contracts/student_learning/get_student_learning_space'

const {
	getStudentLearningSpaceMock,
	getStudentTaskSubmissionMock,
	submitStudentTaskSubmissionMock,
	markStudentTaskCompleteMock,
	createReflectionEntryMock,
	routeState,
	routerReplaceMock,
} =
	vi.hoisted(() => ({
		getStudentLearningSpaceMock: vi.fn(),
		getStudentTaskSubmissionMock: vi.fn(),
		submitStudentTaskSubmissionMock: vi.fn(),
		markStudentTaskCompleteMock: vi.fn(),
		createReflectionEntryMock: vi.fn(),
		routeState: {
			query: {
				student_group: 'GROUP-1',
			},
			hash: '',
		},
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
			setup(props, { slots }) {
				return () =>
					h('a', { 'data-to': JSON.stringify(props.to || null) }, slots.default?.())
			},
		}),
		useRouter: () => ({
			replace: routerReplaceMock,
		}),
		useRoute: () => routeState,
	}
})

vi.mock('@/lib/services/student/studentLearningHubService', () => ({
	getStudentLearningSpace: getStudentLearningSpaceMock,
}))

vi.mock('@/lib/services/student/studentTaskSubmissionService', () => ({
	getStudentTaskSubmission: getStudentTaskSubmissionMock,
	submitStudentTaskSubmission: submitStudentTaskSubmissionMock,
}))

vi.mock('@/lib/services/student/studentTaskCompletionService', () => ({
	markStudentTaskComplete: markStudentTaskCompleteMock,
}))

vi.mock('@/lib/services/portfolio/portfolioService', () => ({
	createReflectionEntry: createReflectionEntryMock,
}))

vi.mock('frappe-ui', () => ({
	toast: {
		success: vi.fn(),
		error: vi.fn(),
	},
}))

import CourseDetail from '@/pages/student/CourseDetail.vue'

const cleanupFns: Array<() => void> = []

function buildAttachmentPreview(overrides: Record<string, unknown> = {}) {
	return {
		item_id: 'MAT-1',
		owner_doctype: 'Supporting Material',
		owner_name: 'MAT-1',
		file_id: 'FILE-1',
		display_name: 'Resource',
		kind: 'other',
		preview_mode: 'icon_only',
		...overrides,
	}
}

function buildLatestSubmission(overrides: Record<string, unknown> = {}) {
	return {
		submission_id: 'TSU-1',
		version: 1,
		submitted_on: '2026-04-01 12:30:00',
		submitted_by: 'student@example.com',
		origin: 'Student Upload',
		is_stub: false,
		evidence_note: null,
		is_cloned: false,
		cloned_from: null,
		text_content: 'Initial lab reflection',
		link_url: 'https://example.com/lab-reflection',
		attachments: [],
		annotation_readiness: null,
		released_result: {
			outcome_id: 'OUT-WRITE-1',
			task_submission: 'TSU-1',
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

function buildPayload(message: string | null = null): StudentLearningSpaceResponse {
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
		communications: {
			course_updates_summary: {
				total_count: 3,
				unread_count: 2,
				high_priority_count: 1,
				has_high_priority: 1,
				latest_publish_at: '2026-04-01T08:00:00',
			},
		},
		message,
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
				task_delivery: 'TDL-WRITE-1',
			},
			reflection_entries: [
				{
					name: 'REF-1',
					entry_date: '2026-04-01',
					entry_type: 'Reflection',
					visibility: 'Teacher',
					moderation_state: 'Draft',
					body: 'Microscope evidence helped me compare the two cell types.',
					body_preview: 'Microscope evidence helped me compare the two cell types.',
					course: 'COURSE-1',
					student_group: 'GROUP-1',
					class_session: 'CLASS-SESSION-1',
				},
			],
			unit_navigation: [
				{
					unit_plan: 'UNIT-PLAN-1',
					title: 'Cells and Systems',
					unit_order: 1,
					session_count: 2,
					assigned_work_count: 2,
					is_current: 1,
				},
			],
		},
		resources: {
			shared_resources: [
				{
					material: 'MAT-SHARED-1',
					title: 'Course field guide',
					file_name: 'field-guide.pdf',
					preview_url: '/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-SHARED-1',
					open_url: '/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-SHARED-1',
					attachment_preview: buildAttachmentPreview({
						item_id: 'MAT-SHARED-1',
						display_name: 'Course field guide',
						kind: 'pdf',
						extension: 'pdf',
						preview_mode: 'pdf_embed',
						preview_url:
							'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-SHARED-1',
						open_url:
							'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-SHARED-1',
					}),
				},
			],
			class_resources: [
				{
					material: 'MAT-CLASS-1',
					title: 'Class microscope labels',
					file_name: 'microscope-labels.png',
					thumbnail_url:
						'/api/method/ifitwala_ed.api.file_access.thumbnail_academic_file?file=FILE-CLASS-1',
					preview_url: '/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-CLASS-1',
					open_url: '/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-CLASS-1',
					attachment_preview: buildAttachmentPreview({
						item_id: 'MAT-CLASS-1',
						display_name: 'Class microscope labels',
						kind: 'image',
						extension: 'png',
						preview_mode: 'thumbnail_image',
						thumbnail_url:
							'/api/method/ifitwala_ed.api.file_access.thumbnail_academic_file?file=FILE-CLASS-1',
						preview_url:
							'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-CLASS-1',
						open_url:
							'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-CLASS-1',
					}),
				},
			],
				general_assigned_work: [
					{
						task_delivery: 'TDL-QUIZ-1',
						task: 'TASK-QUIZ-1',
						title: 'Cell Structure Checkpoint',
						instructions_html:
							'<p>Review the microscope guide, then answer the checkpoint questions.</p>',
						task_type: 'Quiz',
						unit_plan: 'UNIT-PLAN-1',
						class_session: 'CLASS-SESSION-1',
						submission_status: 'Submitted',
						quiz_state: {
							can_continue: 1,
							status_label: 'In Progress',
						},
						materials: [
							{
								material: 'MAT-TASK-1',
								title: 'Checkpoint worksheet',
								description: 'Download the worksheet before you start.',
								file_name: 'checkpoint-worksheet.pdf',
								preview_url:
									'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-TASK-1',
								open_url:
									'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-TASK-1',
								attachment_preview: buildAttachmentPreview({
									item_id: 'MAT-TASK-1',
									display_name: 'Checkpoint worksheet',
									kind: 'pdf',
									extension: 'pdf',
									preview_mode: 'pdf_embed',
									preview_url:
										'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-TASK-1',
									open_url:
										'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-TASK-1',
								}),
							},
							],
						},
						{
							task_delivery: 'TDL-WRITE-1',
							task: 'TASK-WRITE-1',
							task_outcome: 'OUT-WRITE-1',
							title: 'Lab reflection write-up',
							instructions_html:
								'<p>Summarize your microscope evidence and link your final write-up.</p>',
							task_type: 'Written Response',
							unit_plan: 'UNIT-PLAN-1',
							class_session: 'CLASS-SESSION-1',
							delivery_mode: 'Collect Work',
							grading_mode: 'None',
							requires_submission: 1,
							allow_late_submission: 1,
							submission_status: 'Not Submitted',
							materials: [],
						},
					],
		},
		curriculum: {
			counts: {
				units: 1,
				sessions: 2,
				assigned_work: 2,
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
					shared_resources: [
						{
							material: 'MAT-UNIT-1',
							title: 'Cell gallery',
							file_name: 'cell-gallery.webp',
							thumbnail_url:
								'/api/method/ifitwala_ed.api.file_access.thumbnail_academic_file?file=FILE-UNIT-1',
							preview_url: '/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-UNIT-1',
							open_url: '/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-UNIT-1',
							attachment_preview: buildAttachmentPreview({
								item_id: 'MAT-UNIT-1',
								display_name: 'Cell gallery',
								kind: 'image',
								extension: 'webp',
								preview_mode: 'thumbnail_image',
								thumbnail_url:
									'/api/method/ifitwala_ed.api.file_access.thumbnail_academic_file?file=FILE-UNIT-1',
								preview_url:
									'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-UNIT-1',
								open_url:
									'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-UNIT-1',
							}),
						},
					],
						assigned_work: [
							{
								task_delivery: 'TDL-QUIZ-1',
								task: 'TASK-QUIZ-1',
								title: 'Cell Structure Checkpoint',
								instructions_html:
									'<p>Review the microscope guide, then answer the checkpoint questions.</p>',
								task_type: 'Quiz',
								unit_plan: 'UNIT-PLAN-1',
								class_session: 'CLASS-SESSION-1',
								submission_status: 'Submitted',
								quiz_state: {
									can_continue: 1,
									status_label: 'In Progress',
								},
								materials: [
									{
										material: 'MAT-TASK-1',
										title: 'Checkpoint worksheet',
										description: 'Download the worksheet before you start.',
										file_name: 'checkpoint-worksheet.pdf',
										preview_url:
											'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-TASK-1',
										open_url:
											'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-TASK-1',
										attachment_preview: buildAttachmentPreview({
											item_id: 'MAT-TASK-1',
											display_name: 'Checkpoint worksheet',
											kind: 'pdf',
											extension: 'pdf',
											preview_mode: 'pdf_embed',
											preview_url:
												'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-TASK-1',
											open_url:
												'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-TASK-1',
										}),
									},
								],
							},
							{
								task_delivery: 'TDL-WRITE-1',
								task: 'TASK-WRITE-1',
								task_outcome: 'OUT-WRITE-1',
								title: 'Lab reflection write-up',
								instructions_html:
									'<p>Summarize your microscope evidence and link your final write-up.</p>',
								task_type: 'Written Response',
								unit_plan: 'UNIT-PLAN-1',
								class_session: 'CLASS-SESSION-1',
								delivery_mode: 'Collect Work',
								grading_mode: 'None',
								requires_submission: 1,
								allow_late_submission: 1,
								submission_status: 'Not Submitted',
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
							resources: [
								{
									material: 'MAT-1',
									title: 'Microscope guide',
									description: 'Use this guide during the station walk.',
									file_name: 'microscope-guide.pdf',
									preview_url: '/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-1',
									open_url: '/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-1',
									attachment_preview: buildAttachmentPreview({
										item_id: 'MAT-1',
										display_name: 'Microscope guide',
										kind: 'pdf',
										extension: 'pdf',
										preview_mode: 'pdf_embed',
										preview_url:
											'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-1',
										open_url:
											'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-1',
									}),
								},
							],
								assigned_work: [
									{
										task_delivery: 'TDL-QUIZ-1',
										task: 'TASK-QUIZ-1',
										title: 'Cell Structure Checkpoint',
										instructions_html:
											'<p>Review the microscope guide, then answer the checkpoint questions.</p>',
										task_type: 'Quiz',
										unit_plan: 'UNIT-PLAN-1',
										class_session: 'CLASS-SESSION-1',
										submission_status: 'Submitted',
										quiz_state: {
											can_continue: 1,
											status_label: 'In Progress',
										},
										materials: [
											{
												material: 'MAT-TASK-1',
												title: 'Checkpoint worksheet',
												description: 'Download the worksheet before you start.',
												file_name: 'checkpoint-worksheet.pdf',
												preview_url:
													'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-TASK-1',
												open_url:
													'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-TASK-1',
												attachment_preview: buildAttachmentPreview({
													item_id: 'MAT-TASK-1',
													display_name: 'Checkpoint worksheet',
													kind: 'pdf',
													extension: 'pdf',
													preview_mode: 'pdf_embed',
													preview_url:
														'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-TASK-1',
													open_url:
														'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-TASK-1',
												}),
											},
										],
									},
									{
										task_delivery: 'TDL-WRITE-1',
										task: 'TASK-WRITE-1',
										task_outcome: 'OUT-WRITE-1',
										title: 'Lab reflection write-up',
										instructions_html:
											'<p>Summarize your microscope evidence and link your final write-up.</p>',
										task_type: 'Written Response',
										unit_plan: 'UNIT-PLAN-1',
										class_session: 'CLASS-SESSION-1',
										delivery_mode: 'Collect Work',
										grading_mode: 'None',
										requires_submission: 1,
										allow_late_submission: 1,
										submission_status: 'Not Submitted',
										materials: [],
									},
								],
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

function buildAssignOnlyPayload(): StudentLearningSpaceResponse {
	const payload = buildPayload()
	const convertTask = (item: StudentAssignedWork): StudentAssignedWork =>
		item.task_delivery === 'TDL-WRITE-1'
			? {
					...item,
					task_outcome: 'OUT-ASSIGN-1',
					title: 'Field notebook check',
					delivery_mode: 'Assign Only',
					grading_mode: 'Completion',
					requires_submission: 0,
					allow_late_submission: 0,
					submission_status: 'Not Required',
					is_complete: 0,
				}
			: item

	payload.resources.general_assigned_work = payload.resources.general_assigned_work.map(item =>
		convertTask(item)
	)
	payload.curriculum.units = payload.curriculum.units.map(unit => ({
		...unit,
		assigned_work: unit.assigned_work.map(item => convertTask(item)),
		sessions: unit.sessions.map(session => ({
			...session,
			assigned_work: session.assigned_work.map(item => convertTask(item)),
		})),
	}))

	return payload
}

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function resetRouteState() {
	routeState.query = {
		student_group: 'GROUP-1',
	}
	routeState.hash = ''
	routerReplaceMock.mockImplementation(async location => {
		if (location?.query) {
			routeState.query = { ...location.query }
		}
		if ('hash' in (location || {})) {
			routeState.hash = location.hash || ''
		}
	})
}

function mountCourseDetail(
	propOverrides: Partial<{
		course_id: string
		student_group: string
		unit_plan: string
		class_session: string
		task_delivery: string
	}> = {}
) {
	const host = document.createElement('div')
	document.body.appendChild(host)
	window.HTMLElement.prototype.scrollIntoView = vi.fn()

	const app: App = createApp(
		defineComponent({
			render() {
				return h(CourseDetail, {
					course_id: 'COURSE-1',
					student_group: 'GROUP-1',
					...propOverrides,
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
	getStudentLearningSpaceMock.mockReset()
	getStudentTaskSubmissionMock.mockReset()
	submitStudentTaskSubmissionMock.mockReset()
	markStudentTaskCompleteMock.mockReset()
	createReflectionEntryMock.mockReset()
	routerReplaceMock.mockReset()
	resetRouteState()
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

describe('CourseDetail', () => {
	it('renders the class-aware learning space shell', async () => {
		resetRouteState()
		getStudentLearningSpaceMock.mockResolvedValue(buildPayload())
		getStudentTaskSubmissionMock.mockResolvedValue(buildLatestSubmission())

		mountCourseDetail()
		await flushUi()

		expect(getStudentLearningSpaceMock).toHaveBeenCalledWith({
			course_id: 'COURSE-1',
			student_group: 'GROUP-1',
		})

		expect(document.body.textContent).toContain('Learning Space')
		expect(document.body.textContent).toContain('Biology')
		expect(document.body.textContent).toContain('Learning Focus')
		expect(document.body.textContent).toContain('What to do next')
		expect(document.body.textContent).toContain('Class Updates')
		expect(document.body.textContent).toContain('2 new')
		expect(document.body.textContent).toContain('This Unit')
		expect(document.body.textContent).toContain('Assigned Work')
		expect(document.body.textContent).toContain('Resources for this session')
		expect(document.body.textContent).toContain('Work connected to this class')
		expect(document.body.textContent).toContain('Task Workspace')
		expect(document.body.textContent).toContain('Lab reflection write-up')
		expect(document.body.textContent).toContain('Reflection & Journal')
		expect(document.body.textContent).toContain('Recent entries')
		expect(document.body.textContent).toContain(
			'Microscope evidence helped me compare the two cell types.'
		)
		expect(document.body.textContent).toContain('Structure and function are linked in living systems.')
		expect(document.body.textContent).toContain('Microscope evidence walk')
		expect(document.body.textContent).toContain('Observation walk')
		expect(document.body.textContent).toContain('Continue Cell Structure Checkpoint')
		expect(document.body.textContent).toContain('Cell Structure Checkpoint')
		expect(document.body.textContent).toContain(
			'Review the microscope guide, then answer the checkpoint questions.'
		)
		expect(document.body.textContent).toContain('Checkpoint worksheet')
		expect(document.body.textContent).not.toContain('Messages connected to this class')
		expect(document.body.textContent).not.toContain('Microscope materials are ready')
		expect(document.body.textContent).not.toContain('Class plan published')
		expect(document.body.textContent).not.toContain('Planning not published')
		expect(document.body.textContent).not.toContain('Teacher note')
		expect(getStudentTaskSubmissionMock).toHaveBeenCalledWith({ outcome_id: 'OUT-WRITE-1' })

		const headerImage = document.querySelector('header img')
		expect(headerImage).toBeTruthy()
		expect(headerImage?.className).toContain('aspect-square')

		const classUpdatesLink = Array.from(document.querySelectorAll('a')).find(anchor =>
			anchor.textContent?.includes('Class Updates')
		)
		expect(classUpdatesLink).toBeTruthy()
		const classUpdatesHref = classUpdatesLink?.getAttribute('data-to') || ''
		expect(classUpdatesHref).toContain('"name":"student-communications"')
		expect(classUpdatesHref).toContain('"source":"course"')
		expect(classUpdatesHref).toContain('"course_id":"COURSE-1"')
		expect(classUpdatesHref).toContain('"student_group":"GROUP-1"')
	})

	it('loads and resubmits the selected non-quiz task workspace', async () => {
		resetRouteState()
		getStudentLearningSpaceMock.mockResolvedValue(buildPayload())
		getStudentTaskSubmissionMock
			.mockResolvedValueOnce(buildLatestSubmission())
			.mockResolvedValueOnce(
				buildLatestSubmission({
					submission_id: 'TSU-2',
					version: 2,
					text_content: 'Updated lab reflection',
					link_url: 'https://example.com/updated-reflection',
				})
			)
		submitStudentTaskSubmissionMock.mockResolvedValue({
			submission_id: 'TSU-2',
			version: 2,
			outcome_flags: {
				has_submission: true,
				has_new_submission: true,
				submission_status: 'Resubmitted',
			},
		})

		mountCourseDetail({
			unit_plan: 'UNIT-PLAN-1',
			class_session: 'CLASS-SESSION-1',
			task_delivery: 'TDL-WRITE-1',
		})
		await flushUi()

		const responseArea = document.querySelector(
			'textarea[placeholder="Summarize your work, reflection, or answer."]'
		) as HTMLTextAreaElement | null
		const linkField = document.querySelector(
			'input[placeholder="https://example.com/your-work"]'
		) as HTMLInputElement | null

		expect(responseArea?.value).toBe('Initial lab reflection')
		expect(linkField?.value).toBe('https://example.com/lab-reflection')

		if (!responseArea || !linkField) {
			throw new Error('Expected task submission fields to be rendered.')
		}

		responseArea.value = 'Updated lab reflection'
		responseArea.dispatchEvent(new Event('input', { bubbles: true }))
		linkField.value = 'https://example.com/updated-reflection'
		linkField.dispatchEvent(new Event('input', { bubbles: true }))
		await flushUi()

		const submitButton = Array.from(document.querySelectorAll('button')).find(button =>
			button.textContent?.includes('Resubmit task')
		)
		expect(submitButton).toBeTruthy()
		submitButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		expect(submitStudentTaskSubmissionMock).toHaveBeenCalledWith({
			task_outcome: 'OUT-WRITE-1',
			text_content: 'Updated lab reflection',
			link_url: 'https://example.com/updated-reflection',
			files: undefined,
		}, expect.objectContaining({
			onProgress: expect.any(Function),
		}))
		expect(getStudentTaskSubmissionMock).toHaveBeenNthCalledWith(2, {
			outcome_id: 'OUT-WRITE-1',
		})
		expect(document.body.textContent).toContain('Version 2')
		expect(document.body.textContent).toContain('Updated lab reflection')
		expect(document.body.textContent).toContain('Resubmitted')
	})

	it('renders released score and feedback inside the selected task workspace', async () => {
		resetRouteState()
		getStudentLearningSpaceMock.mockResolvedValue(buildPayload())
		getStudentTaskSubmissionMock.mockResolvedValue(
			buildLatestSubmission({
				released_result: {
					outcome_id: 'OUT-WRITE-1',
					task_submission: 'TSU-1',
					grade_visible: true,
					feedback_visible: true,
					publication: {
						feedback_visibility: 'student',
						grade_visibility: 'student',
						derived_from_legacy_outcome: false,
						legacy_outcome_published: false,
					},
					official: {
						score: 18,
						grade: 'A',
						grade_value: 4,
						feedback: 'Strong evidence selection.',
					},
					feedback: {
						task_submission: 'TSU-1',
						submission_version: 1,
						summary: {
							overall: 'Strong evidence selection.',
							strengths: 'Clear observation details.',
							improvements: 'Tighten the final explanation.',
							next_steps: 'Link the evidence back to the claim.',
						},
						items: [
							{
								id: 'TFI-1',
								kind: 'text_quote',
								page: 1,
								intent: 'next_step',
								workflow_state: 'published',
								comment: 'Link this sentence back to your claim.',
								anchor: {
									kind: 'text_quote',
									page: 1,
									quote: 'The nucleus looked darker.',
								},
							},
						],
					},
				},
			})
		)

		mountCourseDetail({
			unit_plan: 'UNIT-PLAN-1',
			class_session: 'CLASS-SESSION-1',
			task_delivery: 'TDL-WRITE-1',
		})
		await flushUi()

		expect(document.body.textContent).toContain('Released result')
		expect(document.body.textContent).toContain('Grade released')
		expect(document.body.textContent).toContain('Feedback released')
		expect(document.body.textContent).toContain('Score 18')
		expect(document.body.textContent).toContain('Grade A')
		expect(document.body.textContent).toContain('Strong evidence selection.')
		expect(document.body.textContent).toContain('Link the evidence back to the claim.')
		expect(document.body.textContent).toContain('Teacher comments')
		expect(document.body.textContent).toContain('Link this sentence back to your claim.')
	})

	it('supports document upload in the selected task workspace', async () => {
		resetRouteState()
		getStudentLearningSpaceMock.mockResolvedValue(buildPayload())
		getStudentTaskSubmissionMock
			.mockResolvedValueOnce(buildLatestSubmission())
			.mockResolvedValueOnce(
				buildLatestSubmission({
					submission_id: 'TSU-3',
					version: 2,
					text_content: 'Updated lab reflection',
					link_url: 'https://example.com/final-reflection',
					attachments: [
						{
							row_name: 'ATT-1',
							kind: 'file',
							file_name: 'lab-report.pdf',
							open_url:
								'/api/method/ifitwala_ed.api.file_access.download_academic_file?file=FILE-UPLOAD-1',
							preview_url:
								'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-UPLOAD-1',
						},
					],
				})
			)
		submitStudentTaskSubmissionMock.mockImplementation(async (_payload, options) => {
			options?.onProgress?.({
				phase: 'uploading',
				loaded: 50,
				total: 100,
				percent: 50,
			})
			return {
				submission_id: 'TSU-3',
				version: 2,
				outcome_flags: {
					has_submission: true,
					has_new_submission: true,
					submission_status: 'Resubmitted',
				},
			}
		})

		mountCourseDetail({
			unit_plan: 'UNIT-PLAN-1',
			class_session: 'CLASS-SESSION-1',
			task_delivery: 'TDL-WRITE-1',
		})
		await flushUi()

		const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement | null
		expect(fileInput).toBeTruthy()
		if (!fileInput) {
			throw new Error('Expected task submission file input to be rendered.')
		}

		const file = new File(['evidence'], 'lab-report.pdf', { type: 'application/pdf' })
		Object.defineProperty(fileInput, 'files', {
			value: [file],
			configurable: true,
		})
		fileInput.dispatchEvent(new Event('change', { bubbles: true }))
		await flushUi()

		expect(document.body.textContent).toContain('Selected files')
		expect(document.body.textContent).toContain('lab-report.pdf')

		const submitButton = Array.from(document.querySelectorAll('button')).find(button =>
			button.textContent?.includes('Resubmit task')
		)
		expect(submitButton).toBeTruthy()
		submitButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		expect(submitStudentTaskSubmissionMock).toHaveBeenCalledWith({
			task_outcome: 'OUT-WRITE-1',
			text_content: 'Initial lab reflection',
			link_url: 'https://example.com/lab-reflection',
			files: [file],
		}, expect.objectContaining({
			onProgress: expect.any(Function),
		}))
		expect(document.body.textContent).toContain('Version 2')
		expect(document.body.textContent).toContain('lab-report.pdf')
	})

	it('marks assign-only tasks complete in the course workspace', async () => {
		resetRouteState()
		getStudentLearningSpaceMock.mockResolvedValue(buildAssignOnlyPayload())
		markStudentTaskCompleteMock.mockResolvedValue({
			task_outcome: 'OUT-ASSIGN-1',
			is_complete: 1,
			completed_on: '2026-04-22 09:15:00',
		})

		mountCourseDetail({
			unit_plan: 'UNIT-PLAN-1',
			class_session: 'CLASS-SESSION-1',
			task_delivery: 'TDL-WRITE-1',
		})
		await flushUi()

		expect(getStudentTaskSubmissionMock).not.toHaveBeenCalled()
		expect(document.body.textContent).toContain('Mark task complete')
		expect(document.body.textContent).toContain(
			'No submission is required. Mark this task complete here once you finish the assigned work.'
		)

		const completeButton = Array.from(document.querySelectorAll('button')).find(button =>
			button.textContent?.includes('Mark task complete')
		)
		expect(completeButton).toBeTruthy()
		completeButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		expect(markStudentTaskCompleteMock).toHaveBeenCalledWith({
			task_outcome: 'OUT-ASSIGN-1',
		})
		expect(document.body.textContent).toContain('Task complete')
		expect(document.body.textContent).toContain('Completed')
	})

	it('keeps the learning space visible when shared-plan messaging is present', async () => {
		resetRouteState()
		getStudentLearningSpaceMock.mockResolvedValue(
			buildPayload('Showing the shared course plan while your class is being assigned.')
		)

		mountCourseDetail()
		await flushUi()

		expect(document.body.textContent).toContain(
			'Showing the shared course plan while your class is being assigned.'
		)
		expect(document.body.textContent).toContain('Learning Focus')
		expect(document.body.textContent).toContain('Cells and Systems')
		expect(document.body.textContent).toContain('Microscope evidence walk')
	})

	it('prefers governed preview routes for learning materials across the student workspace', async () => {
		resetRouteState()
		getStudentLearningSpaceMock.mockResolvedValue(buildPayload())

		mountCourseDetail()
		await flushUi()

		const pdfPreview = document.querySelector('[data-learning-resource-kind="pdf"]')
		expect(pdfPreview).toBeTruthy()
		expect(pdfPreview?.getAttribute('href')).toBe(
			'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-1'
		)
		expect(pdfPreview?.querySelector('img')?.getAttribute('src')).toBe(
			'/api/method/ifitwala_ed.api.file_access.preview_academic_file?file=FILE-1'
		)

		const imagePreview = document.querySelector('[data-learning-resource-kind="image"] img')
		expect(imagePreview?.getAttribute('src')).toBe(
			'/api/method/ifitwala_ed.api.file_access.thumbnail_academic_file?file=FILE-UNIT-1'
		)

			const downloadLinks = Array.from(document.querySelectorAll('a')).filter(anchor =>
				(anchor.textContent || '').includes('Download')
			)
			expect(downloadLinks.length).toBeGreaterThan(0)
			expect(downloadLinks[0]?.getAttribute('href')).toContain(
				'/api/method/ifitwala_ed.api.file_access.download_academic_file?file='
			)
		})

	it('syncs section and session query state without reloading the bootstrap payload', async () => {
		resetRouteState()
		getStudentLearningSpaceMock.mockResolvedValue(buildPayload())

		mountCourseDetail()
		await flushUi()

		const unitButtons = Array.from(document.querySelectorAll('button')).filter(
			button => button.textContent?.includes('Unit 1')
		)
		expect(unitButtons.length).toBeGreaterThan(0)
		unitButtons[0]?.click()
		await flushUi()

		expect(routerReplaceMock).toHaveBeenCalled()
		expect(routeState.query).toMatchObject({
			student_group: 'GROUP-1',
			unit_plan: 'UNIT-PLAN-1',
			class_session: 'CLASS-SESSION-1',
		})
		expect(routeState.hash).toBe('#session-journey')
		expect(getStudentLearningSpaceMock).toHaveBeenCalledTimes(1)
	})
})
