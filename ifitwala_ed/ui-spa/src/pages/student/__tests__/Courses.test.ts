// ifitwala_ed/ui-spa/src/pages/student/__tests__/Courses.test.ts

import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick, type App } from 'vue'

const { getStudentCoursesDataMock } = vi.hoisted(() => ({
	getStudentCoursesDataMock: vi.fn(),
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

vi.mock('@/lib/services/student/studentLearningHubService', () => ({
	getStudentCoursesData: getStudentCoursesDataMock,
}))

import Courses from '@/pages/student/Courses.vue'

const cleanupFns: Array<() => void> = []

async function flushUi() {
	await Promise.resolve()
	await nextTick()
	await Promise.resolve()
	await nextTick()
}

function mountCourses() {
	const host = document.createElement('div')
	document.body.appendChild(host)

	const app: App = createApp(
		defineComponent({
			render() {
				return h(Courses)
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
	getStudentCoursesDataMock.mockReset()
	while (cleanupFns.length) {
		cleanupFns.pop()?.()
	}
	document.body.innerHTML = ''
})

describe('Courses', () => {
	it('shows readiness state on course cards and blocks unopened spaces from linking', async () => {
		getStudentCoursesDataMock.mockResolvedValue({
			academic_years: ['2025-2026'],
			selected_year: '2025-2026',
			courses: [
				{
					course: 'COURSE-1',
					course_name: 'Biology',
					course_group: 'Science',
					course_image: '/files/biology.jpg',
					href: {
						name: 'student-course-detail',
						params: { course_id: 'COURSE-1' },
						query: { student_group: 'GROUP-1' },
					},
					learning_space: {
						source: 'class_teaching_plan',
						status: 'ready',
						status_label: 'Class Ready',
						summary: 'Open your class learning space.',
						cta_label: 'Open class',
						can_open: 1,
						href: {
							name: 'student-course-detail',
							params: { course_id: 'COURSE-1' },
							query: { student_group: 'GROUP-1' },
						},
					},
				},
				{
					course: 'COURSE-2',
					course_name: 'History',
					course_group: 'Humanities',
					course_image: '/files/history.jpg',
					href: null,
					learning_space: {
						source: 'unavailable',
						status: 'awaiting_class_assignment',
						status_label: 'Class Assignment Pending',
						summary:
							'Your class is still being assigned. Check with your academic office if this should already be available.',
						cta_label: 'Not ready yet',
						can_open: 0,
						href: null,
					},
				},
			],
		})

		mountCourses()
		await flushUi()

		const text = document.body.textContent || ''
		expect(text).toContain('My Courses')
		expect(text).toContain('Available courses this year')
		expect(text).toContain('Biology')
		expect(text).toContain('Class Ready')
		expect(text).toContain('Open class')
		expect(text).toContain('History')
		expect(text).toContain('Class Assignment Pending')
		expect(text).toContain('Not ready yet')

		const links = Array.from(document.querySelectorAll('a')).map(node => node.textContent || '')
		expect(links.some(textValue => textValue.includes('Biology'))).toBe(true)
		expect(links.some(textValue => textValue.includes('History'))).toBe(false)

		const mediaFrames = Array.from(document.querySelectorAll('div')).filter(node =>
			node.className.includes('student-hub-media-frame')
		)
		expect(mediaFrames.length).toBeGreaterThan(0)
	})
})
