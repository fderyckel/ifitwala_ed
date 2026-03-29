// ifitwala_ed/ui-spa/src/components/self_enrollment/SelfEnrollmentEditor.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, ref, type App } from 'vue'

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

import SelfEnrollmentEditor from '@/components/self_enrollment/SelfEnrollmentEditor.vue'
import type { Response as ChoiceStateResponse } from '@/types/contracts/self_enrollment/get_self_enrollment_choice_state'
import type { ChoiceSubmitRow } from '@/types/contracts/self_enrollment/save_self_enrollment_choices'

const cleanupFns: Array<() => void> = []

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function buildPayload(courses: ChoiceStateResponse['courses']): ChoiceStateResponse {
	return {
		generated_at: '2026-03-29T10:00:00',
		viewer: {
			actor_type: 'Guardian',
			user: 'guardian@example.com',
		},
		window: {
			selection_window: 'SEW-2026-0059',
			program_offering: 'PO-2026-0001',
			title: '2026 Course Selection',
			program: 'PROG-2026-0001',
			program_label: 'Grade 10',
			school: 'SCH-2026-0001',
			school_label: 'Bangkok Campus',
			academic_year: 'AY-2026',
			status: 'Open',
			due_on: '2026-04-15 17:00:00',
			is_open_now: 1,
			instructions: 'Choose the courses your child prefers.',
		},
		student: {
			student: 'STU-2026-00020',
			full_name: 'Noah Example',
		},
		permissions: {
			can_edit: 1,
			can_submit: 1,
			locked_reason: null,
		},
		request: {
			name: 'PER-2026-0001',
			status: 'Draft',
			academic_year: 'AY-2026',
			program: 'PROG-2026-0001',
			program_offering: 'PO-2026-0001',
			validation_status: 'Not Validated',
			submitted_on: null,
			submitted_by: null,
			can_edit_choices: true,
			can_submit_choices: true,
		},
		summary: {
			has_request: true,
			has_courses: true,
			has_selectable_courses: true,
			can_edit_choices: true,
			ready_for_submit: false,
			required_course_count: 0,
			optional_course_count: courses.length,
			selected_optional_count: courses.filter(course => course.is_selected).length,
		},
		validation: {
			status: 'pending',
			ready_for_submit: false,
			reasons: [],
			violations: [],
			missing_required_courses: [],
			ambiguous_courses: [],
			group_summary: {},
		},
		required_basket_groups: ['Group 4 Sciences'],
		courses,
	}
}

function mountEditor(payload: ChoiceStateResponse) {
	let latestSaveRows: ChoiceSubmitRow[] | null = null
	let latestSubmitRows: ChoiceSubmitRow[] | null = null
	const payloadRef = ref<ChoiceStateResponse | null>(payload)
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			setup() {
				return () =>
					h(SelfEnrollmentEditor, {
						payload: payloadRef.value,
						loading: false,
						saving: false,
						submitting: false,
						errorMessage: '',
						backTo: { name: 'guardian-course-selection' },
						backLabel: 'Back to Family Board',
						overline: 'Guardian Course Selection',
						onRefresh: () => {},
						onSave: (rows: ChoiceSubmitRow[]) => {
							latestSaveRows = rows
						},
						onSubmit: (rows: ChoiceSubmitRow[]) => {
							latestSubmitRows = rows
						},
					})
			},
		})
	)

	app.mount(host)
	cleanupFns.push(() => {
		app.unmount()
		host.remove()
	})

	return {
		getLatestSaveRows: () => latestSaveRows,
		getLatestSubmitRows: () => latestSubmitRows,
	}
}

afterEach(() => {
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

describe('SelfEnrollmentEditor', () => {
	it('guides guardians and auto-fills the selected section and preference rank', async () => {
		const mounted = mountEditor(
			buildPayload([
				{
					course: 'ESS',
					course_name: 'Environmental Systems and Societies',
					required: false,
					basket_groups: ['Group 3 Humanities', 'Group 4 Sciences'],
					applied_basket_group: null,
					choice_rank: null,
					is_selected: false,
					requires_basket_group_selection: false,
					is_explicit_choice: false,
					has_choice_rank: false,
				},
			])
		)

		await flushUi()

		const scienceSectionHeading = Array.from(document.querySelectorAll('h3')).find(
			heading => (heading.textContent || '').trim() === 'Group 4 Sciences'
		)
		const scienceSection = scienceSectionHeading?.closest('section') as HTMLElement | null
		expect(scienceSection).toBeTruthy()

		const checkbox = scienceSection?.querySelector('input[type="checkbox"]') as HTMLInputElement | null
		expect(checkbox).toBeTruthy()
		if (!checkbox) return

		checkbox.checked = true
		checkbox.dispatchEvent(new Event('change', { bubbles: true }))
		await flushUi()

		const rankInput = scienceSection?.querySelector('input[type="number"]') as HTMLInputElement | null
		const countsInSelect = scienceSection?.querySelector('select') as HTMLSelectElement | null

		expect(rankInput?.value).toBe('1')
		expect(countsInSelect?.value).toBe('Group 4 Sciences')
		expect(document.body.textContent || '').toContain(
			'1 is the first choice in this section. We fill this in for you, and you can change it if needed.'
		)

		const saveButton = Array.from(document.querySelectorAll('button')).find(
			button => (button.textContent || '').trim() === 'Save Draft'
		) as HTMLButtonElement | undefined
		expect(saveButton?.disabled).toBe(false)
		saveButton?.click()

		expect(mounted.getLatestSaveRows()).toEqual([
			{
				course: 'ESS',
				applied_basket_group: 'Group 4 Sciences',
				choice_rank: 1,
			},
		])
	})

	it('lets guardians submit the latest unsaved choices directly', async () => {
		const mounted = mountEditor(
			buildPayload([
				{
					course: 'ESS',
					course_name: 'Environmental Systems and Societies',
					required: false,
					basket_groups: ['Group 4 Sciences'],
					applied_basket_group: null,
					choice_rank: null,
					is_selected: false,
					requires_basket_group_selection: false,
					is_explicit_choice: false,
					has_choice_rank: false,
				},
			])
		)

		await flushUi()

		const checkbox = document.querySelector('input[type="checkbox"]') as HTMLInputElement | null
		expect(checkbox).toBeTruthy()
		if (!checkbox) return

		checkbox.checked = true
		checkbox.dispatchEvent(new Event('change', { bubbles: true }))
		await flushUi()

		const submitButton = Array.from(document.querySelectorAll('button')).find(
			button => (button.textContent || '').trim() === 'Submit Selection'
		) as HTMLButtonElement | undefined
		expect(submitButton?.disabled).toBe(false)
		expect(document.body.textContent || '').toContain(
			'Submit uses your latest changes. Save Draft is optional if you want to come back later.'
		)

		submitButton?.click()

		expect(mounted.getLatestSubmitRows()).toEqual([
			{
				course: 'ESS',
				applied_basket_group: 'Group 4 Sciences',
				choice_rank: 1,
			},
		])
	})
})
