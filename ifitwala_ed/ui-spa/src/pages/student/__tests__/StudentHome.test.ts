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
			setup(props, { slots }) {
				return () =>
					h(
						'a',
						{
							'data-to':
								typeof props.to === 'string' ? props.to : JSON.stringify(props.to ?? {}),
						},
						slots.default?.()
					)
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

	it('renders student communication highlights with direct links back into context', async () => {
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
				next_learning_step: null,
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
			communications: {
				center_href: { name: 'student-communications' },
				latest_course_update: {
					kind: 'course',
					title: 'Microscope materials are ready',
					subtitle: 'Biology A',
					publish_at: '2026-04-01T08:00:00',
					href: {
						name: 'student-course-detail',
						params: { course_id: 'COURSE-1' },
						query: { student_group: 'GROUP-1' },
					},
					href_label: 'Open class',
					item_id: 'org::COMM-1',
					source_label: 'Class Update',
				},
				latest_activity_update: {
					kind: 'activity',
					title: 'Football practice moved to court 2',
					subtitle: 'Football Club',
					publish_at: '2026-04-01T16:00:00',
					href: {
						name: 'student-activities',
						query: { program_offering: 'ACT-1' },
					},
					href_label: 'Open activity',
					item_id: 'org::COMM-2',
					source_label: 'Activity Update',
				},
				latest_school_update: {
					kind: 'school',
					title: 'Assembly starts at 8:00',
					subtitle: 'Main Hall',
					publish_at: '2026-04-02T07:30:00',
					href: {
						name: 'student-communications',
						query: { source: 'school', item: 'event::EVENT-1' },
					},
					href_label: 'Open center',
					item_id: 'event::EVENT-1',
					source_label: 'School Event',
				},
			},
		})

		mountStudentHome()
		await flushUi()

		const text = document.body.textContent || ''
		expect(text).toContain('Communication Center')
		expect(text).toContain('Microscope materials are ready')
		expect(text).toContain('Football practice moved to court 2')
		expect(text).toContain('Assembly starts at 8:00')
		expect(text).toContain('Open communication center')
	})

	it('renders snapshot cards as clickable shortcuts', async () => {
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
					subtitle: 'Resume your course work.',
					cta_label: 'Open course',
					status_label: 'Open',
					can_open: 1,
					href: { name: 'student-course-detail', params: { course_id: 'BIO-1' } },
				},
				accessible_courses_count: 4,
				selected_year: '2025-2026',
				orientation: {
					current_class: {
						course: 'BIO-1',
						course_name: 'Biology',
						student_group: 'GRP-1',
						instructors: ['Dr Green'],
						time_slots: [{ time_range: '09:00 - 09:45' }],
						href: { name: 'student-course-detail', params: { course_id: 'BIO-1' } },
					},
					next_class: null,
				},
				work_board: {
					now: [
						{
							task_delivery: 'DEL-1',
							task: 'TASK-1',
							title: 'Lab Notes',
							requires_submission: 1,
							require_grading: 1,
							href: { name: 'student-course-detail', params: { course_id: 'BIO-1' } },
							lane: 'now',
							lane_reason: 'Ready now',
							status_label: 'Open',
							outcome: {
								has_submission: 0,
								has_new_submission: 0,
								is_complete: 0,
							},
						},
					],
					soon: [
						{
							task_delivery: 'DEL-2',
							task: 'TASK-2',
							title: 'Essay Draft',
							requires_submission: 1,
							require_grading: 1,
							href: { name: 'student-course-detail', params: { course_id: 'ENG-1' } },
							lane: 'soon',
							lane_reason: 'Due this week',
							status_label: 'Upcoming',
							outcome: {
								has_submission: 0,
								has_new_submission: 0,
								is_complete: 0,
							},
						},
					],
					later: [],
					done: [
						{
							task_delivery: 'DEL-3',
							task: 'TASK-3',
							title: 'History Reflection',
							requires_submission: 1,
							require_grading: 1,
							href: { name: 'student-course-detail', params: { course_id: 'HIS-1' } },
							lane: 'done',
							lane_reason: 'Completed',
							status_label: 'Done',
							outcome: {
								has_submission: 1,
								has_new_submission: 0,
								is_complete: 1,
							},
						},
					],
				},
				timeline: [],
			},
		})

		mountStudentHome()
		await flushUi()

		const text = document.body.textContent || ''
		expect(text).toContain('Jump back into the right place')
		expect(text).toContain('Courses')
		expect(text).toContain('In Now')
		expect(text).toContain('Coming This Week')
		expect(text).toContain('Recently Done')

		const courseShortcut = Array.from(document.querySelectorAll('a')).find(node =>
			node.textContent?.includes('Courses')
		)
		const inNowShortcut = Array.from(document.querySelectorAll('a')).find(node =>
			node.textContent?.includes('In Now')
		)

		expect(courseShortcut?.getAttribute('data-to')).toContain('student-courses')
		expect(inNowShortcut?.getAttribute('data-to')).toContain('BIO-1')
	})
})
