// ifitwala_ed/ui-spa/src/pages/guardian/__tests__/GuardianCourseSelection.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { getSelfEnrollmentPortalBoardMock } = vi.hoisted(() => ({
	getSelfEnrollmentPortalBoardMock: vi.fn(),
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

vi.mock('@/lib/services/selfEnrollment/selfEnrollmentService', () => ({
	getSelfEnrollmentPortalBoard: getSelfEnrollmentPortalBoardMock,
}))

import GuardianCourseSelection from '@/pages/guardian/GuardianCourseSelection.vue'

const cleanupFns: Array<() => void> = []

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountGuardianCourseSelection() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(GuardianCourseSelection)
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
	getSelfEnrollmentPortalBoardMock.mockReset()
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

describe('GuardianCourseSelection', () => {
	it('renders the family-first selection board from the canonical payload', async () => {
		getSelfEnrollmentPortalBoardMock.mockResolvedValue({
			generated_at: '2026-03-26T10:00:00',
			viewer: { actor_type: 'Guardian', user: 'guardian@example.com' },
			students: [
				{ student: 'STU-1', full_name: 'Amina Example' },
				{ student: 'STU-2', full_name: 'Noah Example' },
			],
			windows: [
				{
					selection_window: 'SEW-1',
					program_offering: 'PO-1',
					program: 'PROG-1',
					program_label: 'Grade 6 MYP',
					school: 'SCH-1',
					school_label: 'International Riverside Campus',
					title: '25-26 IRC-G6 MYP',
					academic_year: 'AY-2026',
					audience: 'Guardian',
					status: 'Open',
					due_on: '2026-04-15 17:00:00',
					is_open_now: 1,
					instructions: 'Choose one language before the deadline.',
					summary: {
						total_students: 2,
						submitted_count: 1,
						pending_count: 1,
						invalid_count: 0,
						approved_count: 0,
					},
					students: [
						{
							student: 'STU-1',
							full_name: 'Amina Example',
							cohort: 'G6',
							request: {
								name: 'PER-1',
								status: 'Draft',
								validation_status: 'Not Validated',
								can_edit: 1,
							},
						},
						{
							student: 'STU-2',
							full_name: 'Noah Example',
							cohort: 'G6',
							request: {
								name: 'PER-2',
								status: 'Submitted',
								validation_status: 'Valid',
								can_edit: 0,
								locked_reason: 'Selection has already been submitted and is now read-only.',
							},
						},
					],
				},
			],
		})

		mountGuardianCourseSelection()
		await flushUi()

		expect(getSelfEnrollmentPortalBoardMock).toHaveBeenCalledWith({})
		const text = document.body.textContent || ''
		expect(text).toContain('Family Course Selection Board')
		expect(text).toContain('25-26 IRC-G6 MYP')
		expect(text).toContain('Choose one language before the deadline.')
		expect(text).toContain('Amina Example')
		expect(text).toContain('Noah Example')
		expect(text).toContain('View Selection')
	})
})
