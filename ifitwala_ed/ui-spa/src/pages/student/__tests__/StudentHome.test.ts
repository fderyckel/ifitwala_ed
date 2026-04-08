// ifitwala_ed/ui-spa/src/pages/student/__tests__/StudentHome.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { getStudentHubHomeMock } = vi.hoisted(() => ({
	getStudentHubHomeMock: vi.fn(),
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

vi.mock('@/components/calendar/StudentCalendar.vue', async () => {
	const { defineComponent, h } = await import('vue')

	return {
		default: defineComponent({
			name: 'StudentCalendarStub',
			setup() {
				return () => h('div', 'Calendar stub')
			},
		}),
	}
})

vi.mock('@/lib/services/student/studentLearningHubService', () => ({
	getStudentHubHome: getStudentHubHomeMock,
}))

import StudentHome from '@/pages/student/StudentHome.vue'

const cleanupFns: Array<() => void> = []

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountStudentHome() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(StudentHome)
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
	getStudentHubHomeMock.mockReset()
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

describe('StudentHome', () => {
	it('renders a disabled next-step CTA when the next course is not ready yet', async () => {
		;(window as Window & { frappe?: unknown }).frappe = {
			session: {
				user_info: {
					fullname: 'Amina Example',
				},
			},
		}

		getStudentHubHomeMock.mockResolvedValue({
			meta: {
				generated_at: '2026-04-02T09:00:00',
				date: '2026-04-02',
				weekday: 'Thursday',
			},
			identity: {
				user: 'student@example.com',
				student: 'STU-1',
				display_name: 'Amina',
			},
			learning: {
				today_classes: [],
				next_learning_step: {
					kind: 'course',
					title: 'Biology',
					subtitle:
						'Your class is still being assigned. Check with your academic office if this should already be available.',
					cta_label: 'Not ready yet',
					status_label: 'Class Assignment Pending',
					can_open: 0,
					href: null,
				},
				accessible_courses_count: 2,
				selected_year: '2025-2026',
				orientation: {
					current_class: null,
					next_class: null,
				},
				work_board: {
					now: [],
					soon: [],
					later: [],
					done: [],
				},
				timeline: [],
			},
		})

		mountStudentHome()
		await flushUi()

		const text = document.body.textContent || ''
		expect(text).toContain('A course is still being prepared')
		expect(text).toContain('Biology')
		expect(text).toContain('Class Assignment Pending')
		expect(text).toContain('Not ready yet')

		const disabledButton = Array.from(document.querySelectorAll('button')).find(node =>
			node.textContent?.includes('Not ready yet')
		) as HTMLButtonElement | undefined
		expect(disabledButton?.disabled).toBe(true)
	})
})
