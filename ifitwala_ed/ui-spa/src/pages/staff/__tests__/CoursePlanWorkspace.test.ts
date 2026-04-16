import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const {
	getStaffCoursePlanSurfaceMock,
	saveGovernedUnitPlanMock,
	routeState,
	routerReplaceMock,
	overlayOpenMock,
} = vi.hoisted(() => ({
	getStaffCoursePlanSurfaceMock: vi.fn(),
	saveGovernedUnitPlanMock: vi.fn(),
	routeState: {
		query: {
			student_group: 'GROUP-1',
		},
		hash: '',
	},
	routerReplaceMock: vi.fn(),
	overlayOpenMock: vi.fn(),
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
				return () => h('a', { 'data-to': JSON.stringify(props.to || null) }, slots.default?.())
			},
		}),
		useRouter: () => ({
			replace: routerReplaceMock,
		}),
		useRoute: () => routeState,
	}
})

vi.mock('@/lib/services/staff/staffTeachingService', () => ({
	getStaffCoursePlanSurface: getStaffCoursePlanSurfaceMock,
	saveCoursePlan: vi.fn(),
	saveGovernedUnitPlan: saveGovernedUnitPlanMock,
	saveQuizQuestionBank: vi.fn(),
}))

vi.mock('@/components/planning/PlanningRichTextField.vue', () => ({
	default: defineComponent({
		name: 'PlanningRichTextFieldStub',
		props: ['modelValue'],
		setup(props) {
			return () => h('div', { class: 'planning-richtext-stub' }, props.modelValue || '')
		},
	}),
}))

vi.mock('@/components/planning/PlanningResourcePanel.vue', () => ({
	default: defineComponent({
		name: 'PlanningResourcePanelStub',
		props: ['anchorDoctype', 'anchorName'],
		setup(props, { emit }) {
			return () =>
				h(
					'button',
					{
						type: 'button',
						class: 'planning-resource-panel-stub',
						'data-anchor-doctype': props.anchorDoctype || '',
						'data-anchor-name': props.anchorName || '',
						onClick: () => emit('changed'),
					},
					'Resource panel'
				)
		},
	}),
}))

vi.mock('@/components/planning/CoursePlanTimelineCard.vue', () => ({
	default: defineComponent({
		name: 'CoursePlanTimelineCardStub',
		props: ['timeline'],
		setup(props) {
			return () => h('div', `Timeline ${props.timeline?.status || 'unknown'}`)
		},
	}),
}))

vi.mock('@/composables/useOverlayStack', () => ({
	useOverlayStack: () => ({
		open: overlayOpenMock,
	}),
}))

vi.mock('frappe-ui', () => ({
	toast: {
		success: vi.fn(),
		error: vi.fn(),
	},
}))

import CoursePlanWorkspace from '@/pages/staff/CoursePlanWorkspace.vue'

const cleanupFns: Array<() => void> = []

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
				return h(CoursePlanWorkspace, {
					coursePlan: 'COURSE-PLAN-1',
					studentGroup: 'GROUP-1',
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
	getStaffCoursePlanSurfaceMock.mockReset()
	saveGovernedUnitPlanMock.mockReset()
	routerReplaceMock.mockReset()
	overlayOpenMock.mockReset()
	window.localStorage.clear()
	while (cleanupFns.length) cleanupFns.pop()?.()
	document.body.innerHTML = ''
})

describe('CoursePlanWorkspace page', () => {
	it('passes student-group context and expands the overview on demand', async () => {
		getStaffCoursePlanSurfaceMock.mockResolvedValue({
			meta: {
				generated_at: '2026-04-11 10:00:00',
				course_plan: 'COURSE-PLAN-1',
			},
			course_plan: {
				course_plan: 'COURSE-PLAN-1',
				record_modified: '2026-04-11 10:00:00',
				title: 'Biology Semester 1 Plan',
				course: 'COURSE-1',
				course_name: 'Biology',
				course_group: 'Science',
				school: 'SCH-1',
				academic_year: '2026-2027',
				cycle_label: 'Semester 1',
				plan_status: 'Active',
				summary: '<p>Shared summary</p>',
				can_manage_resources: 1,
			},
			resolved: {
				unit_plan: null,
				quiz_question_bank: null,
			},
			resources: {
				course_plan_resources: [],
			},
			field_options: {
				academic_years: [],
				programs: [],
			},
			curriculum: {
				units: [],
				unit_count: 0,
				timeline: {
					status: 'blocked',
					reason: 'missing_academic_year',
					message: 'Add an Academic Year first.',
					scope: {},
					terms: [],
					holidays: [],
					units: [],
					summary: {
						scheduled_unit_count: 0,
						unscheduled_unit_count: 0,
						overflow_unit_count: 0,
						instructional_day_count: 0,
					},
				},
			},
			assessment: {
				quiz_question_banks: [],
				selected_quiz_question_bank: null,
			},
		})

		mountPage()
		await flushUi()

		expect(getStaffCoursePlanSurfaceMock).toHaveBeenCalledWith({
			course_plan: 'COURSE-PLAN-1',
			unit_plan: undefined,
			quiz_question_bank: undefined,
			student_group: 'GROUP-1',
		})
		expect(document.body.textContent || '').toContain('Timeline blocked')
		expect(document.body.textContent || '').not.toContain('Save Shared Course Plan')

		const overviewButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Course Plan Overview')
		)
		overviewButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		expect(document.body.textContent || '').toContain('Save Shared Course Plan')
	})

	it('opens the learning standards overlay from the shared alignment rows action', async () => {
		getStaffCoursePlanSurfaceMock.mockResolvedValue({
			meta: {
				generated_at: '2026-04-13 10:00:00',
				course_plan: 'COURSE-PLAN-1',
			},
			course_plan: {
				course_plan: 'COURSE-PLAN-1',
				record_modified: '2026-04-13 10:00:00',
				title: 'Biology Semester 1 Plan',
				course: 'COURSE-1',
				course_name: 'Biology',
				course_group: 'Science',
				school: 'SCH-1',
				academic_year: '2026-2027',
				cycle_label: 'Semester 1',
				plan_status: 'Active',
				summary: '<p>Shared summary</p>',
				can_manage_resources: 1,
			},
			resolved: {
				unit_plan: 'UNIT-1',
				quiz_question_bank: null,
			},
			resources: {
				course_plan_resources: [],
			},
			field_options: {
				academic_years: [],
				programs: [{ value: 'MYP', label: 'MYP' }],
			},
			curriculum: {
				units: [
					{
						unit_plan: 'UNIT-1',
						record_modified: '2026-04-13 10:00:00',
						title: 'Cells and Systems',
						program: 'MYP',
						unit_order: 10,
						unit_status: 'Active',
						is_published: 1,
						overview: '',
						essential_understanding: '',
						misconceptions: '',
						content: '',
						skills: '',
						concepts: '',
						standards: [
							{
								learning_standard: 'LS-1',
								framework_name: 'IB MYP',
								standard_code: 'A1',
								standard_description: 'Investigate effectively.',
							},
						],
						shared_reflections: [],
						class_reflections: [],
						shared_resources: [],
					},
				],
				unit_count: 1,
				timeline: {
					status: 'blocked',
					reason: 'missing_calendar',
					message: 'Add a calendar first.',
					scope: {},
					terms: [],
					holidays: [],
					units: [],
					summary: {
						scheduled_unit_count: 0,
						unscheduled_unit_count: 1,
						overflow_unit_count: 0,
						instructional_day_count: 0,
					},
				},
			},
			assessment: {
				quiz_question_banks: [],
				selected_quiz_question_bank: null,
			},
		})

		mountPage()
		await flushUi()

		const selectStandardsButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Select Standards')
		)
		selectStandardsButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		expect(overlayOpenMock).toHaveBeenCalledWith(
			'learning-standards-picker',
			expect.objectContaining({
				unitPlan: 'UNIT-1',
				unitTitle: 'Cells and Systems',
				unitProgram: 'MYP',
				programLocked: true,
				existingStandards: ['LS-1'],
				onApply: expect.any(Function),
			})
		)
	})

	it('keeps governed resource panels anchored to the shared plan and selected unit', async () => {
		getStaffCoursePlanSurfaceMock.mockResolvedValue({
			meta: {
				generated_at: '2026-04-13 10:00:00',
				course_plan: 'COURSE-PLAN-1',
			},
			course_plan: {
				course_plan: 'COURSE-PLAN-1',
				record_modified: '2026-04-13 10:00:00',
				title: 'Biology Semester 1 Plan',
				course: 'COURSE-1',
				course_name: 'Biology',
				course_group: 'Science',
				school: 'SCH-1',
				academic_year: '2026-2027',
				cycle_label: 'Semester 1',
				plan_status: 'Active',
				summary: '<p>Shared summary</p>',
				can_manage_resources: 1,
			},
			resolved: {
				unit_plan: 'UNIT-1',
				quiz_question_bank: null,
			},
			resources: {
				course_plan_resources: [],
			},
			field_options: {
				academic_years: [],
				programs: [{ value: 'MYP', label: 'MYP' }],
			},
			curriculum: {
				units: [
					{
						unit_plan: 'UNIT-1',
						record_modified: '2026-04-13 10:00:00',
						title: 'Cells and Systems',
						program: 'MYP',
						unit_order: 10,
						unit_status: 'Active',
						is_published: 1,
						overview: '',
						essential_understanding: '',
						misconceptions: '',
						content: '',
						skills: '',
						concepts: '',
						standards: [],
						shared_reflections: [],
						class_reflections: [],
						shared_resources: [],
					},
				],
				unit_count: 1,
				timeline: {
					status: 'blocked',
					reason: 'missing_calendar',
					message: 'Add a calendar first.',
					scope: {},
					terms: [],
					holidays: [],
					units: [],
					summary: {
						scheduled_unit_count: 0,
						unscheduled_unit_count: 1,
						overflow_unit_count: 0,
						instructional_day_count: 0,
					},
				},
			},
			assessment: {
				quiz_question_banks: [],
				selected_quiz_question_bank: null,
			},
		})

		mountPage()
		await flushUi()

		const coursePlanResourcePanel = document.querySelector(
			'[data-anchor-doctype="Course Plan"]'
		) as HTMLButtonElement | null
		const unitResourcePanel = document.querySelector(
			'[data-anchor-doctype="Unit Plan"]'
		) as HTMLButtonElement | null

		expect(coursePlanResourcePanel?.getAttribute('data-anchor-name')).toBe('COURSE-PLAN-1')
		expect(unitResourcePanel?.getAttribute('data-anchor-name')).toBe('UNIT-1')

		const initialLoadCount = getStaffCoursePlanSurfaceMock.mock.calls.length
		coursePlanResourcePanel?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		expect(getStaffCoursePlanSurfaceMock).toHaveBeenCalledTimes(initialLoadCount + 1)
	})

	it('shows compact standard summary cards and expands details on click', async () => {
		getStaffCoursePlanSurfaceMock.mockResolvedValue({
			meta: {
				generated_at: '2026-04-13 10:00:00',
				course_plan: 'COURSE-PLAN-1',
			},
			course_plan: {
				course_plan: 'COURSE-PLAN-1',
				record_modified: '2026-04-13 10:00:00',
				title: 'ELA Semester 1 Plan',
				course: 'COURSE-1',
				course_name: 'English Language Arts',
				course_group: 'Humanities',
				school: 'SCH-1',
				academic_year: '2026-2027',
				cycle_label: 'Semester 1',
				plan_status: 'Active',
				summary: '<p>Shared summary</p>',
				can_manage_resources: 1,
			},
			resolved: {
				unit_plan: 'UNIT-1',
				quiz_question_bank: null,
			},
			resources: {
				course_plan_resources: [],
			},
			field_options: {
				academic_years: [],
				programs: [{ value: 'MYP', label: 'MYP' }],
			},
			curriculum: {
				units: [
					{
						unit_plan: 'UNIT-1',
						record_modified: '2026-04-13 10:00:00',
						title: 'Reading the Plot Arc',
						program: 'MYP',
						unit_order: 6,
						unit_status: 'Active',
						is_published: 1,
						overview: '',
						essential_understanding: '',
						misconceptions: '',
						content: '',
						skills: '',
						concepts: '',
						standards: [
							{
								learning_standard: 'LS-1',
								framework_name: 'Common Core',
								framework_version: '1',
								subject_area: 'English',
								program: 'IB MYP G6',
								strand: 'Reading: Literature',
								substrand: 'Key Ideas and Details',
								standard_code: 'RL.6.3',
								standard_description:
									"Describe how a particular story's or drama's plot unfolds.",
								coverage_level: 'Introduced',
								alignment_strength: 'Exact',
								alignment_type: 'Knowledge',
								notes: 'Use with mentor texts.',
							},
						],
						shared_reflections: [],
						class_reflections: [],
						shared_resources: [],
					},
				],
				unit_count: 1,
				timeline: {
					status: 'blocked',
					reason: 'missing_calendar',
					message: 'Add a calendar first.',
					scope: {},
					terms: [],
					holidays: [],
					units: [],
					summary: {
						scheduled_unit_count: 0,
						unscheduled_unit_count: 1,
						overflow_unit_count: 0,
						instructional_day_count: 0,
					},
				},
			},
			assessment: {
				quiz_question_banks: [],
				selected_quiz_question_bank: null,
			},
		})

		mountPage()
		await flushUi()

		expect(document.body.textContent || '').toContain('Unit 6: Reading the Plot Arc')
		expect(document.body.textContent || '').toContain('Basics')
		expect(document.body.textContent || '').toContain('Core Narrative')
		expect(document.body.textContent || '').toContain('Learning Focus')
		expect(document.body.textContent || '').not.toContain('Unit Workspace')
		expect(document.body.textContent || '').not.toContain('RL.6.3')

		const standardsToggle = document.querySelector(
			'[data-testid="unit-panel-toggle-standards"]'
		) as HTMLButtonElement | null
		expect(standardsToggle).not.toBeNull()
		standardsToggle?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		const pageText = document.body.textContent || ''
		expect(pageText).toContain('RL.6.3')
		expect(pageText).toContain('Reading: Literature')
		expect(pageText).toContain('Key Ideas and Details')
		expect(pageText).toContain('Coverage: Introduced')
		expect(pageText).toContain('Type: Knowledge')
		expect(pageText).toContain('Strength: Exact')
		expect(pageText).toContain("Describe how a particular story's or drama's plot unfolds.")
		expect(pageText).not.toContain('Framework Name')

		const standardCardButton = Array.from(document.querySelectorAll('button')).find(button => {
			const text = button.textContent || ''
			return text.includes('RL.6.3') && text.includes('Describe how a particular story')
		})
		standardCardButton?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		expect(document.body.textContent || '').toContain('Framework Name')
		expect(document.body.textContent || '').toContain('Remove Standard')
	})

	it('keeps the long core narrative collapsed until staff opens it', async () => {
		getStaffCoursePlanSurfaceMock.mockResolvedValue({
			meta: {
				generated_at: '2026-04-13 10:00:00',
				course_plan: 'COURSE-PLAN-1',
			},
			course_plan: {
				course_plan: 'COURSE-PLAN-1',
				record_modified: '2026-04-13 10:00:00',
				title: 'ELA Semester 1 Plan',
				course: 'COURSE-1',
				course_name: 'English Language Arts',
				course_group: 'Humanities',
				school: 'SCH-1',
				academic_year: '2026-2027',
				cycle_label: 'Semester 1',
				plan_status: 'Active',
				summary: '<p>Shared summary</p>',
				can_manage_resources: 1,
			},
			resolved: {
				unit_plan: 'UNIT-1',
				quiz_question_bank: null,
			},
			resources: {
				course_plan_resources: [],
			},
			field_options: {
				academic_years: [],
				programs: [{ value: 'MYP', label: 'MYP' }],
			},
			curriculum: {
				units: [
					{
						unit_plan: 'UNIT-1',
						record_modified: '2026-04-13 10:00:00',
						title: 'Narrative Writing Launch',
						program: 'MYP',
						unit_order: 2,
						unit_status: 'Active',
						is_published: 1,
						overview: '<p>Backbone narrative for the unit.</p>',
						essential_understanding: '<p>Students shape identity through story.</p>',
						misconceptions: '<p>Strong narratives are not just timelines.</p>',
						content: '<p>Memoirs and essays</p>',
						skills: '<p>Close reading and drafting</p>',
						concepts: '<p>Voice and identity</p>',
						standards: [],
						shared_reflections: [],
						class_reflections: [],
						shared_resources: [],
					},
				],
				unit_count: 1,
				timeline: {
					status: 'blocked',
					reason: 'missing_calendar',
					message: 'Add a calendar first.',
					scope: {},
					terms: [],
					holidays: [],
					units: [],
					summary: {
						scheduled_unit_count: 0,
						unscheduled_unit_count: 1,
						overflow_unit_count: 0,
						instructional_day_count: 0,
					},
				},
			},
			assessment: {
				quiz_question_banks: [],
				selected_quiz_question_bank: null,
			},
		})

		mountPage()
		await flushUi()

		expect(document.body.textContent || '').not.toContain('Backbone narrative for the unit.')

		const narrativeToggle = document.querySelector(
			'[data-testid="unit-panel-toggle-narrative"]'
		) as HTMLButtonElement | null
		expect(narrativeToggle).not.toBeNull()
		narrativeToggle?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
		await flushUi()

		expect(document.body.textContent || '').toContain('Backbone narrative for the unit.')
		expect(document.body.textContent || '').toContain('Students shape identity through story.')
		expect(document.body.textContent || '').toContain('Strong narratives are not just timelines.')
	})

	it('shows the sticky save rail after the selected unit becomes dirty', async () => {
		getStaffCoursePlanSurfaceMock.mockResolvedValue({
			meta: {
				generated_at: '2026-04-13 10:00:00',
				course_plan: 'COURSE-PLAN-1',
			},
			course_plan: {
				course_plan: 'COURSE-PLAN-1',
				record_modified: '2026-04-13 10:00:00',
				title: 'Biology Semester 1 Plan',
				course: 'COURSE-1',
				course_name: 'Biology',
				course_group: 'Science',
				school: 'SCH-1',
				academic_year: '2026-2027',
				cycle_label: 'Semester 1',
				plan_status: 'Active',
				summary: '<p>Shared summary</p>',
				can_manage_resources: 1,
			},
			resolved: {
				unit_plan: 'UNIT-1',
				quiz_question_bank: null,
			},
			resources: {
				course_plan_resources: [],
			},
			field_options: {
				academic_years: [],
				programs: [{ value: 'MYP', label: 'MYP' }],
			},
			curriculum: {
				units: [
					{
						unit_plan: 'UNIT-1',
						record_modified: '2026-04-13 10:00:00',
						title: 'Cells and Systems',
						program: 'MYP',
						unit_order: 10,
						unit_status: 'Active',
						is_published: 1,
						overview: '<p>Overview</p>',
						essential_understanding: '<p>Understanding</p>',
						misconceptions: '<p>Misconception</p>',
						content: '<p>Content</p>',
						skills: '<p>Skills</p>',
						concepts: '<p>Concepts</p>',
						standards: [],
						shared_reflections: [],
						class_reflections: [],
						shared_resources: [],
					},
				],
				unit_count: 1,
				timeline: {
					status: 'blocked',
					reason: 'missing_calendar',
					message: 'Add a calendar first.',
					scope: {},
					terms: [],
					holidays: [],
					units: [],
					summary: {
						scheduled_unit_count: 0,
						unscheduled_unit_count: 1,
						overflow_unit_count: 0,
						instructional_day_count: 0,
					},
				},
			},
			assessment: {
				quiz_question_banks: [],
				selected_quiz_question_bank: null,
			},
		})

		mountPage()
		await flushUi()

		expect(document.querySelector('[data-testid="unit-save-rail"]')).toBeNull()

		const unitCodeInput = document.querySelector(
			'input[placeholder="Optional unit code"]'
		) as HTMLInputElement | null
		expect(unitCodeInput).not.toBeNull()
		if (!unitCodeInput) return

		unitCodeInput.value = 'BIO-U1'
		unitCodeInput.dispatchEvent(new Event('input', { bubbles: true }))
		await flushUi()

		expect(document.querySelector('[data-testid="unit-save-rail"]')).not.toBeNull()
		expect(document.body.textContent || '').toContain('Unsaved changes')
		expect(
			(document.querySelector('[data-testid="unit-save-header-button"]') as HTMLButtonElement | null)
				?.disabled
		).toBe(false)
	})
})
