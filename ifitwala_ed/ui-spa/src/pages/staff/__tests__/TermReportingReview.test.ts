import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { getSurfaceMock, queueActionMock } = vi.hoisted(() => ({
	getSurfaceMock: vi.fn(),
	queueActionMock: vi.fn(),
}))

vi.mock('frappe-ui', async () => {
	const { defineComponent, h } = await import('vue')

	return {
		FeatherIcon: defineComponent({
			name: 'FeatherIconStub',
			props: { name: { type: String, required: false, default: '' } },
			setup(props) {
				return () => h('span', { 'data-feather-icon': props.name })
			},
		}),
	}
})

vi.mock('@/components/filters/FiltersBar.vue', async () => {
	const { defineComponent, h } = await import('vue')

	return {
		default: defineComponent({
			name: 'FiltersBarStub',
			setup(_props, { slots }) {
				return () => h('section', { 'data-testid': 'filters-bar' }, slots.default?.())
			},
		}),
	}
})

vi.mock('@/lib/services/termReporting/termReportingService', () => ({
	getTermReportingReviewSurface: getSurfaceMock,
	queueTermReportingReviewAction: queueActionMock,
}))

import router from '@/router'
import TermReportingReview from '@/pages/staff/TermReportingReview.vue'

const cleanupFns: Array<() => void> = []

const reviewSurface = {
	cycles: [
		{
			name: 'RC-1',
			school: 'SCH-1',
			academic_year: 'AY-2026',
			term: 'TERM-1',
			program: 'PROG-1',
			assessment_scheme: 'ASC-1',
			assessment_calculation_method: 'Weighted Categories',
			name_label: 'Semester 1 Report',
			task_cutoff_date: '2026-04-01',
			status: 'Calculated',
		},
	],
	selected_reporting_cycle: 'RC-1',
	cycle: {
		reporting_cycle: 'RC-1',
		school: 'SCH-1',
		academic_year: 'AY-2026',
		term: 'TERM-1',
		program: 'PROG-1',
		status: 'Calculated',
		assessment_scheme: 'ASC-1',
		assessment_calculation_method: 'Weighted Categories',
		name_label: 'Semester 1 Report',
		task_cutoff_date: '2026-04-01',
		course_term_results: 1,
	},
	filters: {
		reporting_cycle: 'RC-1',
		course: null,
		student: null,
		program: null,
	},
	results: {
		rows: [
			{
				name: 'CTR-1',
				student: 'STU-1',
				program_enrollment: 'PE-1',
				course: 'COURSE-1',
				program: 'PROG-1',
				academic_year: 'AY-2026',
				term: 'TERM-1',
				assessment_scheme: 'ASC-1',
				assessment_calculation_method: 'Weighted Categories',
				grade_scale: 'GS-1',
				numeric_score: 88.5,
				grade_value: 'A',
				override_grade_value: null,
				task_counted: 4,
				total_weight: 100,
				internal_note: 'Review complete',
				components: [
					{
						component_type: 'Category',
						component_key: 'Summative',
						label: 'Summative Evidence',
						assessment_category: 'Summative',
						assessment_criteria: null,
						weight: 70,
						raw_score: 90,
						weighted_score: 63,
						grade_value: 'A',
						evidence_count: 3,
						included_outcome_count: 3,
						excluded_outcome_count: 0,
						calculation_note: null,
					},
				],
			},
		],
		total_count: 1,
		page_count: 1,
		start: 0,
		limit: 50,
	},
	readiness: {
		status: 'attention',
		ready: true,
		counts: {
			total_results: 1,
			zero_task_results: 0,
			missing_score_results: 0,
			missing_grade_results: 0,
			override_results: 1,
			missing_teacher_comment_results: 0,
			missing_component_results: 0,
		},
		blocked_reasons: [],
		warnings: ['1 result(s) contain grade overrides for review.'],
		actions: {
			can_recalculate: true,
			recalculate_block_reason: null,
			can_generate_reports: true,
			generate_reports_block_reason: null,
		},
	},
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
				return h(TermReportingReview)
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
	getSurfaceMock.mockReset()
	queueActionMock.mockReset()
	while (cleanupFns.length) cleanupFns.pop()?.()
	document.body.innerHTML = ''
})

describe('TermReportingReview route', () => {
	it('registers the staff term reporting review route', () => {
		const route = router.getRoutes().find(route => route.name === 'staff-term-reporting')
		expect(route?.path).toBe('/staff/term-reporting')
		expect(route?.meta.layout).toBe('staff')
	})
})

describe('TermReportingReview page', () => {
	it('loads the review surface and applies detail filters through the service payload', async () => {
		getSurfaceMock.mockResolvedValue(reviewSurface)

		mountPage()
		await flushUi()

		expect(getSurfaceMock).toHaveBeenCalledWith({ limit: 50, start: 0 })
		expect(document.querySelector('[data-testid="filters-bar"]')).not.toBeNull()
		expect(document.querySelector('.staff-shell')).not.toBeNull()
		expect(document.body.textContent || '').toContain('Term Reporting Review')
		expect(document.body.textContent || '').toContain('Semester 1 Report')
		expect(document.body.textContent || '').toContain('STU-1')
		expect(document.body.textContent || '').toContain('COURSE-1')
		expect(document.body.textContent || '').toContain('Summative Evidence')
		expect(document.body.textContent || '').toContain('Readiness')
		expect(document.body.textContent || '').toContain('Review Needed')

		const courseInput = document.querySelector(
			'[data-testid="term-reporting-course-filter"]'
		) as HTMLInputElement
		courseInput.value = 'COURSE-1'
		courseInput.dispatchEvent(new Event('input', { bubbles: true }))

		const applyButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Apply')
		) as HTMLButtonElement
		applyButton.click()
		await flushUi()

		expect(getSurfaceMock).toHaveBeenLastCalledWith({
			reporting_cycle: 'RC-1',
			course: 'COURSE-1',
			limit: 50,
			start: 0,
		})
	})

	it('queues reporting actions from the readiness panel', async () => {
		getSurfaceMock.mockResolvedValue(reviewSurface)
		queueActionMock.mockResolvedValue({
			queued: true,
			action: 'recalculate_course_results',
			reporting_cycle: 'RC-1',
		})

		mountPage()
		await flushUi()

		const recalculateButton = Array.from(document.querySelectorAll('button')).find(button =>
			(button.textContent || '').includes('Recalculate')
		) as HTMLButtonElement
		recalculateButton.click()
		await flushUi()

		expect(queueActionMock).toHaveBeenCalledWith({
			reporting_cycle: 'RC-1',
			action: 'recalculate_course_results',
		})
		expect(document.body.textContent || '').toContain('Course result recalculation was queued')
	})
})
