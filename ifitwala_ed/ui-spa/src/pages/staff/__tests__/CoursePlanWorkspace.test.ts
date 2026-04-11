import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { getStaffCoursePlanSurfaceMock, routeState, routerReplaceMock, overlayOpenMock } = vi.hoisted(() => ({
	getStaffCoursePlanSurfaceMock: vi.fn(),
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
	saveGovernedUnitPlan: vi.fn(),
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
		setup() {
			return () => h('div', 'Resource panel')
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
})
